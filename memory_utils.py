import torch
import matplotlib.pyplot as plt


def _get_gpu_mem(synchronize=True, empty_cache=True):
    return torch.cuda.memory_allocated(), torch.cuda.memory_cached()


def _generate_mem_hook(handle_ref, mem, idx, hook_type, exp):
    def hook(self, *args):
        if len(mem) == 0 or mem[-1]["exp"] != exp:
            call_idx = 0
        else:
            call_idx = mem[-1]["call_idx"] + 1

        mem_all, mem_cached = _get_gpu_mem()
        torch.cuda.synchronize()
        mem.append({
            'layer_idx': idx,
            'call_idx': call_idx,
            'layer_type': type(self).__name__,
            'exp': exp,
            'hook_type': hook_type,
            'mem_all': mem_all,
            'mem_cached': mem_cached,
        })

    return hook


def _add_memory_hooks(idx, mod, mem_log, exp, hr):
    h = mod.register_forward_pre_hook(_generate_mem_hook(hr, mem_log, idx, 'pre', exp))
    hr.append(h)

    h = mod.register_forward_hook(_generate_mem_hook(hr, mem_log, idx, 'fwd', exp))
    hr.append(h)

    h = mod.register_backward_hook(_generate_mem_hook(hr, mem_log, idx, 'bwd', exp))
    hr.append(h)


def log_mem(model, optimizer, inp, mem_log=None, exp=None):
    mem_log = mem_log or []
    exp = exp or f'exp_{len(mem_log)}'
    hr = []
    for idx, module in enumerate(model.modules()):
        _add_memory_hooks(idx, module, mem_log, exp, hr)

    try:
        optimizer.zero_grad()
        out = model(input_ids=inp[0], labels=inp[1], attention_mask=inp[2])
        loss = out.loss
        loss.backward()
        optimizer.step()
    finally:
        [h.remove() for h in hr]

        return mem_log


def plot_mem(df, exps=["baseline"]):
    fig, axs = plt.subplots(1, 2, figsize=(20, 5))
    fig.suptitle('Memory usage')

    axs[0].plot(df["mem_all"])
    axs[0].set_xlabel("call_idx")
    axs[0].set_ylabel("mem_all, Mb")

    axs[1].plot(df["mem_cached"])
    axs[1].set_xlabel("call_idx")
    axs[1].set_ylabel("mem_cached, Mb")

    plt.show()
