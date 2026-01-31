"""
API routes for the Coding Agent.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...auth import get_current_user
from ...models import User
from ....coding_agent import CodingAgent


router = APIRouter(prefix="/coding", tags=["coding"])

# Store agents per user session
_agents: dict[int, CodingAgent] = {}


def get_agent(user: User = Depends(get_current_user)) -> CodingAgent:
    """Get or create coding agent for user."""
    if user.id not in _agents:
        _agents[user.id] = CodingAgent(language="he")
    return _agents[user.id]


class CodeInput(BaseModel):
    """Input for code operations."""
    code: str
    language: str = "python"


class MessageInput(BaseModel):
    """Input for agent messages."""
    message: str


class GenerateInput(BaseModel):
    """Input for code generation."""
    type: str  # "function", "class", "pattern"
    name: str
    args: Optional[list[tuple[str, str]]] = None
    description: Optional[str] = None


class AgentResponseModel(BaseModel):
    """Response from coding agent."""
    message: str
    code: Optional[str] = None
    language: str = "python"
    suggestions: list[str] = []
    success: bool = True


@router.post("/process", response_model=AgentResponseModel)
async def process_message(
    input: MessageInput,
    agent: CodingAgent = Depends(get_agent)
):
    """Process a message through the coding agent."""
    response = agent.process(input.message)
    return AgentResponseModel(
        message=response.message,
        code=response.code,
        language=response.language,
        suggestions=response.suggestions,
        success=response.success
    )


@router.post("/analyze")
async def analyze_code(
    input: CodeInput,
    agent: CodingAgent = Depends(get_agent)
):
    """Analyze code and return metrics."""
    metrics = agent.analyzer.analyze_code(input.code, input.language)
    return {
        "lines_of_code": metrics.lines_of_code,
        "blank_lines": metrics.blank_lines,
        "comment_lines": metrics.comment_lines,
        "functions": metrics.functions,
        "classes": metrics.classes,
        "imports": metrics.imports,
        "complexity": metrics.complexity,
        "issues": metrics.issues
    }


@router.post("/explain")
async def explain_code(
    input: CodeInput,
    agent: CodingAgent = Depends(get_agent)
):
    """Explain code in natural language."""
    explanation = agent.explainer.explain(input.code)
    return {
        "summary": explanation.summary,
        "detailed": explanation.detailed,
        "concepts": explanation.concepts,
        "suggestions": explanation.suggestions
    }


@router.post("/generate", response_model=AgentResponseModel)
async def generate_code(
    input: GenerateInput,
    agent: CodingAgent = Depends(get_agent)
):
    """Generate code based on specifications."""
    if input.type == "function":
        result = agent.generator.generate_function(
            name=input.name,
            args=input.args or [("param", "Any")],
            return_type="Any",
            description=input.description or f"Function {input.name}"
        )
    elif input.type == "class":
        result = agent.generator.generate_class(
            name=input.name,
            attributes=[("name", "str")],
            methods=["process"],
            description=input.description or f"Class {input.name}"
        )
    elif input.type == "pattern":
        result = agent.generator.generate_pattern(input.name, "MyClass")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown type: {input.type}")

    return AgentResponseModel(
        message=f"Generated {input.type}: {input.name}",
        code=result.code,
        language=result.language,
        success=True
    )


@router.post("/review")
async def review_code(
    input: CodeInput,
    agent: CodingAgent = Depends(get_agent)
):
    """Review code and provide feedback."""
    metrics = agent.analyzer.analyze_code(input.code)
    explanation = agent.explainer.explain(input.code)

    # Calculate quality score
    score = 100
    if metrics.issues:
        score -= len(metrics.issues) * 10
    if metrics.complexity > 10:
        score -= (metrics.complexity - 10) * 5
    if not metrics.comment_lines:
        score -= 10
    score = max(0, score)

    return {
        "score": score,
        "issues": metrics.issues,
        "suggestions": explanation.suggestions,
        "metrics": {
            "lines_of_code": metrics.lines_of_code,
            "complexity": metrics.complexity,
            "functions": len(metrics.functions),
            "classes": len(metrics.classes)
        }
    }


@router.post("/run")
async def run_code(
    input: CodeInput,
    agent: CodingAgent = Depends(get_agent)
):
    """Run Python code and return output."""
    if input.language != "python":
        raise HTTPException(status_code=400, detail="Only Python execution is supported")

    response = agent._cmd_run(input.code)
    return {
        "success": response.success,
        "output": response.message
    }


@router.get("/templates")
async def list_templates(language: str = "python"):
    """List available code templates."""
    from ....coding_agent import CodeGenerator
    generator = CodeGenerator()
    return {
        "templates": generator.list_templates(language),
        "patterns": generator.list_patterns()
    }


@router.post("/set-language")
async def set_language(
    language: str,
    agent: CodingAgent = Depends(get_agent)
):
    """Set agent output language."""
    if language not in ["he", "en"]:
        raise HTTPException(status_code=400, detail="Language must be 'he' or 'en'")
    agent.set_language(language)
    return {"message": f"Language set to {language}"}


@router.get("/conversation")
async def get_conversation(agent: CodingAgent = Depends(get_agent)):
    """Get conversation history."""
    return {
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "code": msg.code,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in agent.conversation
        ],
        "summary": agent.get_conversation_summary()
    }


@router.delete("/conversation")
async def clear_conversation(agent: CodingAgent = Depends(get_agent)):
    """Clear conversation history."""
    agent.clear_conversation()
    return {"message": "Conversation cleared"}
