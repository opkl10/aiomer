"""
Coding Agent - AI-powered coding assistant module.
Provides code analysis, generation, explanation, and debugging capabilities.
"""

from .agent import CodingAgent
from .analyzer import CodeAnalyzer
from .generator import CodeGenerator
from .explainer import CodeExplainer

__all__ = ["CodingAgent", "CodeAnalyzer", "CodeGenerator", "CodeExplainer"]
