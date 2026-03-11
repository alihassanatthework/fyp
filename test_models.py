from core.ai_models.xgboost_severity import XGBoostSeverityClassifier
from core.ai_models.llm_recommender import LLMRecommender

# Test XGBoost (without trained model - should use fallback)
# xgboost = XGBoostSeverityClassifier()
# result = xgboost.classify_severity({'confidence': 0.75, 'condition_type': 'acne'}, 'acne')
# print("XGBoost result:", result)
from core.ai_models import XGBoostSeverityClassifier

x = XGBoostSeverityClassifier()  # Uses fallback (no model file)
r = x.classify_severity({'confidence': 0.5}, 'acne')
print(r)

# Test LLM (with API)
llm = LLMRecommender(api_key="your-key", use_api=True)
routine = llm.generate_care_routine(
    {'detected_conditions': [{'name': 'acne', 'confidence': 0.7}]},
    {'age': 25, 'skin_type': 'oily'},
    {'allergies': []}
)
print("LLM result:", routine)