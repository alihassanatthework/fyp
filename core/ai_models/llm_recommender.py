"""
LLM-based recommendation engine module.

This module provides functionality for generating personalized care
recommendations using Large Language Models.
"""

import json
import os
from typing import Dict, List, Optional

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class LLMRecommender:
    """
    LLM-based recommendation engine.

    Attributes:
        model: Loaded LLM model or API client
        api_key: API key for external LLM service (if using API)
    """

    def __init__(self, model_path=None, api_key=None, use_api=False, model_name='gpt-3.5-turbo'):
        self.use_api = use_api
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model_path = model_path
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.client = None

        if use_api:
            if OPENAI_AVAILABLE and self.api_key:
                self.client = OpenAI(api_key=self.api_key)
                print(f"✅ LLM API client initialized (model: {model_name})")
            else:
                print("⚠️ OpenAI not available or API key missing")
        else:
            if TRANSFORMERS_AVAILABLE and model_path:
                try:
                    self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                    self.model = AutoModelForCausalLM.from_pretrained(
                        model_path,
                        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                        device_map='auto' if torch.cuda.is_available() else None
                    )
                    print(f"✅ Local LLM model loaded from {model_path}")
                except Exception as e:
                    print(f"⚠️ Failed to load local LLM: {e}")
            else:
                print("⚠️ Transformers not available or model_path missing")

    def _build_prompt(self, analysis_results, user_profile, medical_history):
        """Build prompt for LLM."""
        conditions = analysis_results.get('detected_conditions', [])
        severity_scores = analysis_results.get('severity_scores', {})

        condition_text = []
        for cond in conditions:
            name = cond.get('name', 'unknown')
            severity_info = severity_scores.get(name, {})
            level = severity_info.get('level', 'Mild')
            condition_text.append(f"- {name.replace('_', ' ').title()}: {level} severity")

        allergies = medical_history.get('allergies', [])
        pregnancy = medical_history.get('is_pregnant', False)
        medical_text = []
        if allergies:
            medical_text.append(f"Allergies: {', '.join(allergies)}")
        if pregnancy:
            medical_text.append("Pregnant: Yes")

        age = user_profile.get('age', 'Unknown')
        skin_type = user_profile.get('skin_type', 'Unknown')

        prompt = f"""You are a dermatology assistant. Generate personalized skincare recommendations.

Patient Profile:
- Age: {age}
- Skin Type: {skin_type}

Detected Conditions:
{chr(10).join(condition_text) if condition_text else '- No conditions detected'}

Medical History:
{chr(10).join(medical_text) if medical_text else '- No significant medical history'}

Please provide:
1. Daily care routine (morning and evening)
2. Weekly care suggestions
3. Product recommendations (avoiding allergens)
4. When to consult a dermatologist

Format your response as JSON with this structure:
{{
    "daily_routine": {{
        "morning": ["step1", "step2"],
        "evening": ["step1", "step2"]
    }},
    "weekly_routine": ["suggestion1", "suggestion2"],
    "products": [
        {{"name": "product name", "type": "cleanser/moisturizer/etc", "reason": "why recommended"}}
    ],
    "dermatologist_consult": "when to consult"
}}
"""
        return prompt

    def _generate(self, prompt):
        """Generate response from LLM."""
        if self.use_api and self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are a helpful dermatology assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"⚠️ LLM API call failed: {e}")
                return None
        elif self.model and self.tokenizer:
            try:
                inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
                if torch.cuda.is_available():
                    inputs = {k: v.to('cuda') for k, v in inputs.items()}

                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=500,
                        do_sample=True
                    )

                response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                response = response[len(prompt):].strip()
                return response
            except Exception as e:
                print(f"⚠️ Local LLM generation failed: {e}")
                return None
        else:
            print("⚠️ LLM not initialized")
            return None

    def _parse_response(self, response):
        """Parse LLM response into structured format."""
        if not response:
            return {
                'daily_routine': {'morning': [], 'evening': []},
                'weekly_routine': [],
                'products': [],
                'dermatologist_consult': 'Consult if condition worsens'
            }

        try:
            if '```json' in response:
                json_start = response.find('```json') + 7
                json_end = response.find('```', json_start)
                response = response[json_start:json_end].strip()
            elif '```' in response:
                json_start = response.find('```') + 3
                json_end = response.find('```', json_start)
                response = response[json_start:json_end].strip()

            return json.loads(response)
        except json.JSONDecodeError:
            return {
                'daily_routine': {'morning': [], 'evening': []},
                'weekly_routine': [],
                'products': [],
                'dermatologist_consult': response[:200] if response else 'Consult if condition worsens'
            }

    def generate_care_routine(self, analysis_results, user_profile, medical_history):
        """Generate personalized care routine."""
        prompt = self._build_prompt(analysis_results, user_profile, medical_history)
        response = self._generate(prompt)
        return self._parse_response(response)

    def recommend_products(self, conditions, severity, medical_history):
        """Recommend products based on conditions and medical history."""
        allergies = medical_history.get('allergies', [])
        prompt = f"""Recommend skincare products for these conditions: {', '.join(conditions)}.
Severity levels: {severity}
Allergies to avoid: {', '.join(allergies) if allergies else 'None'}

Return JSON format:
{{
    "products": [
        {{"name": "product", "type": "type", "reason": "why", "safe_for_allergies": true}}
    ]
}}
"""
        response = self._generate(prompt)
        parsed = self._parse_response(response)
        return parsed.get('products', [])

    def generate_explanation(self, condition, detection_data):
        """Generate explanation for AI detection."""
        confidence = detection_data.get('confidence', 0.0)
        regions = detection_data.get('regions', [])
        prompt = f"""Explain this AI detection in simple terms:
Condition: {condition}
Confidence: {confidence:.0%}
Regions detected: {len(regions)}

Provide a brief, friendly explanation (2-3 sentences) about what this condition means and what the user should know.
"""
        response = self._generate(prompt)
        return response if response else f"{condition.replace('_', ' ').title()} was detected with {confidence:.0%} confidence."
