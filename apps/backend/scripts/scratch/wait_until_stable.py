  # 判断文件是否稳定，如果稳定了才能进行后续处理
  # 如果超时也返回false

import time
import os

def wait_until_stable(path:str,checks: int = 3, interval: float = 1.0, timeout: float = 10) -> bool:
  last_size = -1
  stable = 0
  start_time = time.time()
  while stable < checks:
    if time.time() - start_time > timeout: return False
    if not os.path.exists(path):
      return False
    size = os.path.getsize(path)
    if size == last_size and size >= 0:
      stable += 1
    else:
      stable = 0
      last_size = size
    time.sleep(interval)
  return True