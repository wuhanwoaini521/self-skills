"""项目级 conftest：确保仓库根目录在 sys.path 中，tests 可导入 tools / skills 模块。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
