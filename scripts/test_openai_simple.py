#!/usr/bin/env python3
"""
簡單測試 OpenAI backend 發送 HI 並取得回應
"""
import os
import sys

# 切換到 refactor 目錄
os.chdir('/home/edward/twinkle_code_eval/refactor')

# 添加路徑
sys.path.extend(['.', '..'])

def test_openai_simple():
    """簡單測試 OpenAI backend"""
    print("🚀 測試 OpenAI Backend 簡單調用...")
    
    try:
        # 導入 OpenAI 生成器
        from backend.openai.openai import OpenaiGenerator
        
        print("✅ OpenAI 生成器導入成功")
        
        # 創建生成器實例
        # 你可以在這裡設置 API 配置
        generator = OpenaiGenerator(
            model_name="gpt-3.5-turbo",  # 或其他模型名稱
            model_type="Chat",
            temperature=0.0,
            max_tokens=100
        )
        
        print("✅ OpenAI 生成器初始化成功")
        
        # 準備測試提示 - 使用原始格式
        test_prompts = ["HI"]
        
        print("📤 發送測試訊息: HI")
        
        # 調用生成
        responses = generator.generate(
            prompts=test_prompts,
            num_samples=1,
            response_prefix=""
        )
        
        print("📥 收到回應:")
        for i, response_list in enumerate(responses):
            print(f"   Prompt {i+1}: {test_prompts[i]}")
            for j, response in enumerate(response_list):
                print(f"   Response {j+1}: {response}")
                print("   Status: 200 OK" if response and not response.startswith("# Error") else "   Status: Error")
        
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("OpenAI Backend 簡單測試")
    print("=" * 50)
    
    success = test_openai_simple()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 測試完成 - OpenAI Backend 可以正常調用")
    else:
        print("❌ 測試失敗 - 需要檢查配置或實現")
    
    print("=" * 50)
    
    sys.exit(0 if success else 1)