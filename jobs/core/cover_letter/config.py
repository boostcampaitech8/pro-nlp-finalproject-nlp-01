"""
Cover Letter Generation Configuration
llm-pipeline의 settings.py 설정을 그대로 반영
"""

# LLM 설정 (HyperCLOVA X) - 자소서 생성 전용
# LLM 설정 (HyperCLOVA X) - 자소서 생성 전용
LLM_MODEL = "HCX-007"
LLM_TEMPERATURE = 0.0   # 사실 기반 생성 (할루시네이션 원천 차단을 위해 0.0 설정)
LLM_TOP_P = 0.8        # 안정적 어휘 (API 기본값과 동일하나, 명시적 고정)
LLM_REPETITION_PENALTY = 1.2  # 문장 반복 방지 (기본값 1.1보다 높게 설정하여 반복 억제 강화)
LLM_MAX_TOKENS = 32768  # 긴 자소서 생성을 위해 최대치 설정

# Thinking 설정 (HCX-007 이상)
LLM_USE_THINKING = True
LLM_THINKING_LEVEL = "high"  # budget_tokens 등 구체적 값은 나중에 매핑

# 검색 설정
SEARCH_TOP_K = 5

# 청킹 설정 (현재 사용하지 않지만 향후 확장용)
CHUNK_SIZE = 800
CHUNK_OVERLAP = 160
