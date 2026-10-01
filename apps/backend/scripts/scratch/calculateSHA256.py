# 计算文件的sha256

import hashlib
import os
# from ..log import logger

# 计算单文件的sha256值
def calculate_sha256_from_file(file_path: str)-> str:
  try:
    with open(file_path, 'rb') as f:
      sha256_hash = hashlib.sha256()
      for byte_block in iter(lambda: f.read(4096), b""):
        sha256_hash.update(byte_block)
    # logger.info(f"SHA256 calculated for file: {file_path}")
    print(f"SHA256 calculated for file: {file_path}")
    return sha256_hash.hexdigest()
  except Exception as e:
    # logger.error(f"Error occurred while calculating SHA256: {e}")
    print(f"Error occurred while calculating SHA256: {e}")
    return None

# 计算文件夹的sha256值,暂时不考虑针对不同资源的文件夹进行不同的处理
"""
当前直接计算文件夹中所有文件的sha256值，并将这些值进行拼接后再计算最终的sha256值。
为了保证计算结果的稳定性，文件夹中的文件会按照文件名进行排序后再进行计算。
"""
def calculate_sha256_from_directory(directory_path: str)-> str:
  # 获取目录下所有文件的路径
  file_paths = []
  for root, dirs, files in os.walk(directory_path):
    for file in files:
      file_paths.append(os.path.join(root, file))
  file_paths.sort()  # 按文件名排序

  # 计算每个文件的sha256值并拼接
  sha256_values = []
  for file_path in file_paths:
    sha256_value = calculate_sha256_from_file(file_path)
    if sha256_value:
      sha256_values.append(sha256_value)

  # 计算最终的sha256值
  if sha256_values:
    final_sha256 = hashlib.sha256()
    for value in sha256_values:
      final_sha256.update(value.encode())
    # logger.info(f"SHA256 calculated for directory: {directory_path}")
    print(f"SHA256 calculated for directory: {directory_path}")
    return final_sha256.hexdigest()
  else:
    # logger.error(f"Error occurred while calculating SHA256 for directory: {directory_path}")
    print(f"Error occurred while calculating SHA256 for directory: {directory_path}")
    return None