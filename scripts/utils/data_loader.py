import os

def load_dict_fr_txt(file_path='../data/.repoignore') -> set:
    """
    从 *.txt 加载并返回一个包含所有要过滤的集合 (set)。
    集合提供了 O(1) 的平均时间复杂度的查找效率。
    """
    if not os.path.exists(file_path):
        return set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip()}
    except IOError as e:
        print(f"错误: 无法读取隐藏文件 '{file_path}': {e}")
        return set()


def get_filtered(src_list: list[dict], filter_dict: set, defind_key:str) -> list[dict]:
    filtered_iterator = filter(
        lambda repo: repo.get(defind_key) not in filter_dict,
        src_list
    )
    return list(filtered_iterator)