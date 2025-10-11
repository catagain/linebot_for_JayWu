import json
import string

def load_addresses_data():
    try:
        with open('available_addresses.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_addresses_data(data):
    with open('available_addresses.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def transform_address(input_str):
    """
    將 "數字+字母" 的字串格式轉換為 "數字樓之中文數字" 的格式。
    例如: "1A" -> "1樓之一", "2B" -> "2樓之二"
    假設字母為大寫，且從 A 開始依序代表 1, 2, 3, ...

    :param input_str: 原始字串 (例如 "1A", "2B")
    :return: 轉換後的字串 (例如 "1樓之一", "2樓之二")
    """
    if len(input_str) < 2:
        return input_str  # 如果字串太短，無法處理，則返回原始字串

    # 1. 拆分字串
    # 假設第一個字元或多個連續數字是樓層，最後一個字元是字母
    floor_part = input_str[:-1]  # 取得除了最後一個字元以外的部分 (樓層)
    letter_part = input_str[-1]  # 取得最後一個字元 (字母)

    # 2. 字母轉換成數字
    # 使用 ord() 函數取得字母的 ASCII 值
    # 大寫字母 'A' 的 ASCII 值是 65
    # 所以 'A' 對應 1 (65 - 65 + 1 = 1)
    # 'B' 對應 2 (66 - 65 + 1 = 2)
    try:
        letter_number = ord(letter_part.upper()) - ord('A') + 1
    except TypeError:
        # 如果最後一個字元不是單個字元，則返回錯誤訊息或原始字串
        return f"錯誤: 最後一個字元 '{letter_part}' 無法識別為單一字母。"

    # 3. 數字轉換成中文數字
    chinese_numbers = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    if 1 <= letter_number <= 10:
        chinese_num = chinese_numbers[letter_number]
    else:
        # 如果數字超出預期範圍 (例如 'K' = 11 或更多)，則用原始數字
        chinese_num = str(letter_number) # 或者你可以選擇一個更複雜的中文數字轉換函數

    # 4. 組合成目標格式
    result = f"{floor_part}樓之{chinese_num}"
    return result

addr_list = load_addresses_data()

addr_prefix = input("請輸入想要變更的案名：") 
new_addr = input("請輸入新的地址:")

if addr_list:
    for item in addr_list:
        if item['address'].startswith(addr_prefix):
            item["old_name"] = item['address']
            item['address'] = new_addr + '_' + transform_address(item['old_name'].split('_')[1])
            item['property_type'] = '成屋'

    print(f"將 {addr_prefix} 由預售屋更改為成屋")

    save_addresses_data(addr_list)

    print("已更改完成")

else :
    print("available_addresses.json not found.")



