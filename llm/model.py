# import torch
# from transformers import AutoModelForImageTextToText, AutoProcessor, TextIteratorStreamer, BitsAndBytesConfig
# from core.load_settings import load_settings
# from threading import Thread

# class LLMModel:
#     def __init__(self):
#         settings = load_settings()
#         llm_settings = settings.get('llm', {})
        
#         self.model_name = llm_settings.get('model_name', 'Qwen/Qwen2-VL-2B-Instruct')
#         self.device = llm_settings.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
#         self.max_new_tokens = llm_settings.get('max_new_tokens', 512)
#         self.temperature = llm_settings.get('temperature', 0.1)
#         self.top_p = llm_settings.get('top_p', 0.9)
#         self.load_in_4bit = llm_settings.get('load_in_4bit', True)

#         print(f"Loading model: {self.model_name} on {self.device}...")
        
#         bnb_config = None
#         if self.load_in_4bit and self.device == 'cuda':
#             try:
#                 bnb_config = BitsAndBytesConfig(
#                     load_in_4bit=True,
#                     bnb_4bit_compute_dtype=torch.float16,
#                     bnb_4bit_quant_type="nf4",
#                     bnb_4bit_use_double_quant=True,
#                 )
#             except Exception as e:
#                 print(f"Failed to load BitsAndBytesConfig: {e}. Falling back to standard loading.")

#         try:
#             self.processor = AutoProcessor.from_pretrained(self.model_name)
#             self.model = AutoModelForImageTextToText.from_pretrained(
#                 self.model_name,
#                 quantization_config=bnb_config,
#                 device_map="auto" if self.device == 'cuda' else None,
#                 torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
#                 trust_remote_code=True
#             )
            
#             if self.device != 'cuda':
#                 self.model.to(self.device)
#         except Exception as e:
#             print(f"Error loading model: {e}")
#             # Mock model for testing if real model fails to load in restricted environment
#             self.model = None

#     def generate(self, messages: list) -> str:
#         if self.model is None:
#             return "Đây là câu trả lời mẫu từ hệ thống (Model chưa được tải thành công)."

#         inputs = self.processor.apply_chat_template(
#             messages,
#             add_generation_prompt=True,
#             tokenize=True,
#             return_dict=True,
#             return_tensors="pt",
#         ).to(self.device)

#         generation_kwargs = dict(
#             **inputs,
#             max_new_tokens=self.max_new_tokens,
#             temperature=self.temperature,
#             top_p=self.top_p,
#             do_sample=True if self.temperature > 0 else False,
#             pad_token_id=self.processor.tokenizer.eos_token_id
#         )

#         output_ids = self.model.generate(**generation_kwargs)
        
#         # We need to extract only the newly generated tokens
#         generated_ids = [
#             output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, output_ids)
#         ]
        
#         response = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
#         return response


import torch
import json
from transformers import AutoModelForImageTextToText, AutoProcessor, TextIteratorStreamer, BitsAndBytesConfig
from core.load_settings import load_settings
from threading import Thread

class LLMModel:
    def __init__(self):
        settings = load_settings()
        llm_settings = settings.get('llm', {})
        
        self.model_name = llm_settings.get('model_name', 'Qwen/Qwen2-VL-2B-Instruct')
        self.device = llm_settings.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
        self.max_new_tokens = llm_settings.get('max_new_tokens', 1024) # Tăng thêm để trả lời chi tiết
        self.temperature = llm_settings.get('temperature', 0.1)
        self.load_in_4bit = llm_settings.get('load_in_4bit', True)

        print(f"Loading model: {self.model_name}...")
        
        bnb_config = None
        if self.load_in_4bit and self.device == 'cuda':
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )

        self.processor = AutoProcessor.from_pretrained(self.model_name)
        self.model = AutoModelForImageTextToText.from_pretrained(
            self.model_name,
            quantization_config=bnb_config,
            device_map="auto" if self.device == 'cuda' else None,
            torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
            trust_remote_code=True
        )

    def generate_with_tools(self, messages: list, tools: list = None):
        """
        Phiên bản generate hỗ trợ Tools (Function Calling). 
        Sử dụng đồng bộ vì Function Calling thường cần xử lý xong response mới biết có gọi tool hay không.
        """
        if self.model is None:
            return None

        # Apply chat template với tools
        inputs = self.processor.apply_chat_template(
            messages,
            tools=tools,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.device)

        generation_kwargs = dict(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            do_sample=True if self.temperature > 0 else False,
            pad_token_id=self.processor.tokenizer.eos_token_id
        )

        output_ids = self.model.generate(**generation_kwargs)
        
        # Chỉ lấy phần mới được sinh ra
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, output_ids)
        ]
        
        # Decode kết quả. Lưu ý: Qwen2-VL sẽ trả về định dạng đặc biệt nếu có tool call
        response_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        # Thử parse tool calls nếu có
        # Đối với Qwen2, tool calls thường nằm trong response_text với định dạng cụ thể hoặc qua processor
        # Ở đây ta giả định LLM sẽ sinh ra văn bản chứa tool calls theo format của template
        return response_text

    def stream_generate(self, messages: list, tools: list = None):
        if self.model is None:
            yield "Model error."
            return

        inputs = self.processor.apply_chat_template(
            messages,
            tools=tools,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.device)

        streamer = TextIteratorStreamer(self.processor.tokenizer, skip_prompt=True, skip_special_tokens=True)

        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            do_sample=True if self.temperature > 0 else False,
            pad_token_id=self.processor.tokenizer.eos_token_id
        )

        # Chạy generate trong một thread riêng để không chặn việc stream
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()

        for new_text in streamer:
            yield new_text
