# VoxKeep

[![CI](https://github.com/zaviro/voxkeep/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/zaviro/voxkeep/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

VoxKeep 是面向 Linux 桌面的本地常驻语音链路：持续监听麦克风，检测唤醒词，使用
VAD + ASR 捕获一句完整语音，再把最终文本注入当前输入框，或分发到 `openclaw agent`
等动作。

## 快速开始

项目使用 Python 3.11；所有 Python 命令均通过 `uv` 运行。

```bash
make setup-ai-models
make validate-config
make run
```

`make setup-ai-models` 会同步开发和运行时 AI 依赖，并准备当前启用规则所需的唤醒模型。
`make run` 会确保仓库管理的 FunASR 容器已启动，然后在宿主机运行 VoxKeep，以便访问
麦克风和桌面输入接口。第一次启动可能需要下载镜像和模型。

`make doctor` 包含一次真实的 FunASR WebSocket 健康检查，因此应在 ASR 服务已经可达时
运行；全新安装无需在第一次 `make run` 前执行它。

当前唯一支持的 ASR 后端是 `funasr_ws`。默认服务地址为
`ws://127.0.0.1:10096/`；Compose 将该端口映射到容器内的 `10095`。Qwen/vLLM 已不受
支持，不应恢复相关配置、适配器或 fallback。

完整部署、外部 FunASR 配置和故障排查见
[`docs/operations.md`](docs/operations.md)。

## 工作方式

```text
麦克风
  -> audio engine
      |-> wake audio -> WakeEvent ---------|
      |-> VAD audio  -> VadEvent ----------|-> 统一捕获事件队列 -> capture FSM
      |-> ASR audio  -> AsrFinalEvent -----|                         |
                              |                                      v
                              |                               CaptureCommand
                              |                                  |       |
                              |                                  v       v
                              |----------------------------> storage   injection / openclaw action
```

运行时是一个模块化单体：`bootstrap` 负责组装和生命周期，各业务模块通过自己的
`public.py` 暴露最小 API，跨模块消息定义在 `shared/events.py`。只有 audio engine
可以打开麦克风，只有 storage 模块可以写 SQLite。

从 [`docs/architecture.md`](docs/architecture.md) 开始阅读源码；其中给出了推荐阅读顺序、
模块职责、线程模型和边界约束。

## CLI

```bash
uv run --python 3.11 python -m voxkeep --help
```

主要命令：

- `run --config <path>`：启动本地运行时。
- `doctor`：检查桌面会话、麦克风、AI 依赖、注入工具和 ASR 健康状态。
- `check`：顺序执行 Ruff、Pyright 和 pytest。
- `config validate --config <path>`：验证 YAML 和 `VOXKEEP_*` 环境变量覆盖。
- `backend doctor --config <path>`：对当前 ASR 地址执行 WebSocket 健康检查。

不带子命令时仍按 `run` 处理，以兼容已有调用方式。

## 项目结构

```text
src/voxkeep/
  bootstrap/       # 运行时组装、生命周期和健康监控
  modules/
    audio_engine/  # 麦克风采集、预处理和 audio bus
    capture/       # wake/VAD、句子状态机和命令生成
    transcription/ # FunASR 适配与转写事件
    injection/     # 文本注入与动作执行
    storage/       # SQLite 持久化
  shared/          # 配置、事件、日志和队列工具
  cli/             # 操作入口
tests/
  unit/
  integration/
  e2e/
  architecture/
```

退役的 `core`、`infra`、`services` 命名空间已删除；不要重新添加运行时代码。

## 配置

主配置文件是 `config/config.yaml`：

- 顶层 `max_queue_size`：统一控制运行时有界队列容量。
- `asr.*`：FunASR WebSocket 地址、重连和 2-pass 参数。
- `wake.rules[]`：每个唤醒词各自的阈值和动作路由。
- `vad.*`、`capture.*`：语音边界和捕获窗口。
- `injector.*`：`auto`、`xdotool` 或 `ydotool`。
- `actions.openclaw_agent`：命令模板和超时。
- `storage.*`：SQLite 和可选 JSONL 输出。

配置校验会拒绝未知字段，包括旧的全局 `wake.threshold`、`storage.store_final_only` 和
模块级队列容量字段；唤醒阈值只配置在规则中，队列容量只配置顶层 `max_queue_size`。

默认采样率为 16 kHz，内部帧长为 32 ms。注入后端 `auto` 在 X11 使用 `xdotool`，
在 Wayland 使用 `ydotool`。

## 开发

日常反馈回路：

```bash
make sync
make fmt
make lint
make typecheck
make test-fast
```

完整测试：

```bash
make test
```

`tests/unit` 和 `tests/architecture` 是默认快速测试；涉及 worker、队列、生命周期或模块
接线时，还应运行 `make test-integration`。贡献约定和完整质量门槛见
[`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 文档

- [`docs/architecture.md`](docs/architecture.md)：当前架构和代码阅读地图。
- [`docs/operations.md`](docs/operations.md)：安装、运行、外部服务和故障排查。
- [`docs/funasr-runtime-baseline.md`](docs/funasr-runtime-baseline.md)：FunASR 协议与部署基线。
