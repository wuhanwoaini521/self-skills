"""项目级 conftest：确保仓库根目录在 sys.path 中，tests 可导入 tools / skills 模块。"""

import importlib.util
import os
import sys
from pathlib import Path

REPO_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(REPO_ROOT))


def load_skill_module(relative_path: str, module_name: str):
    """按路径加载 skill 自带的脚本。

    `skills/` 下的脚本不是 python 包，用 importlib 加载可以保证测试直接跑的是
    仓库里的 canonical 副本，而不是 tools/ 下的拷贝。
    """

    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
