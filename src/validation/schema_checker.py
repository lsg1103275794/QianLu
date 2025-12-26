import json
from jsonschema import validate, ValidationError
from typing import Dict, Any, Optional

# 加载 Alpaca schema
SCHEMA_PATH = Path(__file__).parent.parent / "config" / "validation_rules" / "alpaca_schema.json"

def load_schema(schema_path: Path = SCHEMA_PATH) -> Optional[Dict[str, Any]]:
    """加载 JSON Schema 文件。"""
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
        print(f"错误: 无法加载 Alpaca schema 文件 {schema_path}: {e}")
        return None

ALPACA_SCHEMA = load_schema()

def validate_alpaca(instance: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    使用 JSON Schema 校验 Alpaca 格式实例。
    返回 (是否有效, 错误信息或 None)。
    """
    if ALPACA_SCHEMA is None:
        print("错误: Alpaca schema 未加载，无法进行校验。")
        return False, "Schema not loaded."

    try:
        validate(instance=instance, schema=ALPACA_SCHEMA)
        return True, None
    except ValidationError as e:
        # 提供更清晰的错误信息
        error_message = f"Validation failed: {e.message} (path: {'/'.join(map(str, e.path))})"
        return False, error_message
    except Exception as e: # 捕获其他可能的错误
         print(f"校验过程中发生意外错误: {e}")
         return False, f"Unexpected validation error: {str(e)}"

if __name__ == '__main__':
    # 测试
    valid_instance = {"instruction": "Analyze", "input": "Some text", "output": '{"structure": "...", "framework": "...", "style": "..."}'}
    invalid_instance_missing_key = {"instruction": "Analyze", "input": "Some text"}
    invalid_instance_wrong_type = {"instruction": 123, "input": "Some text", "output": "analysis"}

    is_valid, error = validate_alpaca(valid_instance)
    print(f"Valid instance: Is valid? {is_valid}, Error: {error}")

    is_valid, error = validate_alpaca(invalid_instance_missing_key)
    print(f"Invalid instance (missing key): Is valid? {is_valid}, Error: {error}")

    is_valid, error = validate_alpaca(invalid_instance_wrong_type)
    print(f"Invalid instance (wrong type): Is valid? {is_valid}, Error: {error}")