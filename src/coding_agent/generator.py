"""
Code Generator - Generate code snippets and templates.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GeneratedCode:
    """Result of code generation."""
    code: str
    language: str
    description: str
    imports: list[str]


class CodeGenerator:
    """Generates code snippets and templates based on requirements."""

    TEMPLATES = {
        "python": {
            "function": '''def {name}({args}) -> {return_type}:
    """
    {docstring}

    Args:
{args_docs}

    Returns:
        {return_doc}
    """
    {body}
''',
            "class": '''class {name}{bases}:
    """
    {docstring}
    """

    def __init__(self{init_args}):
        """Initialize {name}."""
{init_body}
{methods}
''',
            "async_function": '''async def {name}({args}) -> {return_type}:
    """
    {docstring}

    Args:
{args_docs}

    Returns:
        {return_doc}
    """
    {body}
''',
            "dataclass": '''@dataclass
class {name}:
    """
    {docstring}
    """
{fields}
''',
            "test_function": '''def test_{name}():
    """Test {description}."""
    # Arrange
    {arrange}

    # Act
    {act}

    # Assert
    {assertions}
''',
            "api_endpoint": '''@router.{method}("{path}")
async def {name}({params}):
    """
    {docstring}
    """
    {body}
''',
        },
        "javascript": {
            "function": '''/**
 * {docstring}
{params_jsdoc}
 * @returns {{{return_type}}} {return_doc}
 */
function {name}({args}) {{
    {body}
}}
''',
            "arrow_function": '''/**
 * {docstring}
 */
const {name} = ({args}) => {{
    {body}
}};
''',
            "class": '''/**
 * {docstring}
 */
class {name}{extends} {{
    constructor({args}) {{
        {constructor_body}
    }}
{methods}
}}
''',
            "async_function": '''/**
 * {docstring}
 */
async function {name}({args}) {{
    {body}
}}
''',
        },
        "typescript": {
            "interface": '''/**
 * {docstring}
 */
interface {name}{extends} {{
{properties}
}}
''',
            "type": '''/**
 * {docstring}
 */
type {name} = {definition};
''',
            "function": '''/**
 * {docstring}
{params_jsdoc}
 * @returns {return_doc}
 */
function {name}({args}): {return_type} {{
    {body}
}}
''',
            "class": '''/**
 * {docstring}
 */
class {name}{extends}{implements} {{
    constructor({args}) {{
        {constructor_body}
    }}
{methods}
}}
''',
        },
    }

    COMMON_PATTERNS = {
        "singleton": {
            "python": '''class {name}:
    """Singleton pattern implementation."""
    _instance: Optional["{name}"] = None

    def __new__(cls) -> "{name}":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            # Initialize your singleton here
''',
            "javascript": '''class {name} {{
    static #instance = null;

    constructor() {{
        if ({name}.#instance) {{
            return {name}.#instance;
        }}
        {name}.#instance = this;
        // Initialize your singleton here
    }}

    static getInstance() {{
        if (!{name}.#instance) {{
            {name}.#instance = new {name}();
        }}
        return {name}.#instance;
    }}
}}
''',
        },
        "factory": {
            "python": '''class {name}Factory:
    """Factory pattern for creating {name} instances."""

    _creators: dict[str, type] = {{}}

    @classmethod
    def register(cls, key: str, creator: type) -> None:
        """Register a creator for a given key."""
        cls._creators[key] = creator

    @classmethod
    def create(cls, key: str, **kwargs) -> "{name}":
        """Create an instance based on the key."""
        creator = cls._creators.get(key)
        if not creator:
            raise ValueError(f"Unknown type: {{key}}")
        return creator(**kwargs)
''',
        },
        "observer": {
            "python": '''from abc import ABC, abstractmethod
from typing import Any


class Observer(ABC):
    """Abstract observer interface."""

    @abstractmethod
    def update(self, *args: Any, **kwargs: Any) -> None:
        """Receive update from subject."""
        pass


class Subject:
    """Subject that notifies observers of changes."""

    def __init__(self):
        self._observers: list[Observer] = []

    def attach(self, observer: Observer) -> None:
        """Attach an observer."""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        """Detach an observer."""
        self._observers.remove(observer)

    def notify(self, *args: Any, **kwargs: Any) -> None:
        """Notify all observers."""
        for observer in self._observers:
            observer.update(*args, **kwargs)
''',
        },
    }

    def __init__(self):
        self._custom_templates: dict[str, dict[str, str]] = {}

    def generate_function(
        self,
        name: str,
        args: list[tuple[str, str]],
        return_type: str,
        description: str,
        body: str = "pass",
        language: str = "python",
        is_async: bool = False,
    ) -> GeneratedCode:
        """Generate a function definition."""
        template_key = "async_function" if is_async else "function"
        template = self.TEMPLATES.get(language, {}).get(template_key, "")

        if not template:
            return GeneratedCode(
                code=f"# Template not available for {language}",
                language=language,
                description=description,
                imports=[]
            )

        if language == "python":
            args_str = ", ".join(f"{name}: {type_}" for name, type_ in args)
            args_docs = "\n".join(f"        {name}: {type_}" for name, type_ in args)

            code = template.format(
                name=name,
                args=args_str,
                return_type=return_type,
                docstring=description,
                args_docs=args_docs if args else "        None",
                return_doc=return_type,
                body=body
            )
        else:
            args_str = ", ".join(f"{name}: {type_}" for name, type_ in args)
            params_jsdoc = "\n".join(f" * @param {{{type_}}} {name}" for name, type_ in args)

            code = template.format(
                name=name,
                args=args_str,
                return_type=return_type,
                docstring=description,
                params_jsdoc=params_jsdoc,
                return_doc=return_type,
                body=body
            )

        return GeneratedCode(
            code=code.strip(),
            language=language,
            description=f"Generated function: {name}",
            imports=[]
        )

    def generate_class(
        self,
        name: str,
        attributes: list[tuple[str, str]],
        methods: list[str],
        description: str,
        bases: Optional[list[str]] = None,
        language: str = "python",
    ) -> GeneratedCode:
        """Generate a class definition."""
        template = self.TEMPLATES.get(language, {}).get("class", "")

        if not template:
            return GeneratedCode(
                code=f"# Template not available for {language}",
                language=language,
                description=description,
                imports=[]
            )

        if language == "python":
            bases_str = f"({', '.join(bases)})" if bases else ""
            init_args = ", ".join(f"{attr}: {type_}" for attr, type_ in attributes)
            if init_args:
                init_args = ", " + init_args
            init_body = "\n".join(f"        self.{attr} = {attr}" for attr, _ in attributes)
            if not init_body:
                init_body = "        pass"
            methods_str = "\n\n".join(f"    def {m}(self):\n        pass" for m in methods)

            code = template.format(
                name=name,
                bases=bases_str,
                docstring=description,
                init_args=init_args,
                init_body=init_body,
                methods=methods_str
            )
        else:
            extends_str = f" extends {bases[0]}" if bases else ""
            args_str = ", ".join(f"{attr}" for attr, _ in attributes)
            constructor_body = "\n        ".join(f"this.{attr} = {attr};" for attr, _ in attributes)
            if not constructor_body:
                constructor_body = "// Initialize"
            methods_str = "\n\n".join(f"    {m}() {{\n        // TODO\n    }}" for m in methods)

            code = template.format(
                name=name,
                extends=extends_str,
                docstring=description,
                args=args_str,
                constructor_body=constructor_body,
                methods=methods_str,
                implements=""
            )

        return GeneratedCode(
            code=code.strip(),
            language=language,
            description=f"Generated class: {name}",
            imports=[]
        )

    def generate_pattern(
        self,
        pattern_name: str,
        class_name: str,
        language: str = "python"
    ) -> GeneratedCode:
        """Generate a design pattern implementation."""
        patterns = self.COMMON_PATTERNS.get(pattern_name, {})
        template = patterns.get(language, "")

        if not template:
            available = list(self.COMMON_PATTERNS.keys())
            return GeneratedCode(
                code=f"# Pattern '{pattern_name}' not available. Available: {available}",
                language=language,
                description=f"Pattern not found: {pattern_name}",
                imports=[]
            )

        code = template.format(name=class_name)

        imports = []
        if language == "python":
            if "Optional" in code:
                imports.append("from typing import Optional")
            if "ABC" in code:
                imports.append("from abc import ABC, abstractmethod")
            if "Any" in code:
                imports.append("from typing import Any")

        return GeneratedCode(
            code=code.strip(),
            language=language,
            description=f"Generated {pattern_name} pattern for {class_name}",
            imports=imports
        )

    def generate_test(
        self,
        function_name: str,
        description: str,
        test_cases: list[dict],
        language: str = "python"
    ) -> GeneratedCode:
        """Generate test code for a function."""
        if language != "python":
            return GeneratedCode(
                code="// Test generation only supported for Python",
                language=language,
                description=description,
                imports=[]
            )

        tests = []
        for i, case in enumerate(test_cases):
            test_name = case.get("name", f"case_{i+1}")
            inputs = case.get("inputs", {})
            expected = case.get("expected", None)

            arrange = "\n    ".join(f"{k} = {repr(v)}" for k, v in inputs.items())
            act = f"result = {function_name}({', '.join(inputs.keys())})"
            assertion = f"assert result == {repr(expected)}"

            test_code = self.TEMPLATES["python"]["test_function"].format(
                name=f"{function_name}_{test_name}",
                description=f"{function_name} - {test_name}",
                arrange=arrange or "pass",
                act=act,
                assertions=assertion
            )
            tests.append(test_code)

        code = "\n\n".join(tests)

        return GeneratedCode(
            code=code.strip(),
            language=language,
            description=f"Generated tests for {function_name}",
            imports=["import pytest"]
        )

    def generate_api_endpoint(
        self,
        name: str,
        path: str,
        method: str,
        params: list[tuple[str, str]],
        description: str,
        body: str = "pass"
    ) -> GeneratedCode:
        """Generate a FastAPI endpoint."""
        params_str = ", ".join(f"{p}: {t}" for p, t in params)

        code = self.TEMPLATES["python"]["api_endpoint"].format(
            method=method.lower(),
            path=path,
            name=name,
            params=params_str,
            docstring=description,
            body=body
        )

        return GeneratedCode(
            code=code.strip(),
            language="python",
            description=f"Generated API endpoint: {method.upper()} {path}",
            imports=["from fastapi import APIRouter", "router = APIRouter()"]
        )

    def generate_dataclass(
        self,
        name: str,
        fields: list[tuple[str, str, Optional[str]]],
        description: str
    ) -> GeneratedCode:
        """Generate a Python dataclass."""
        fields_str = "\n".join(
            f"    {fname}: {ftype}" + (f" = {default}" if default else "")
            for fname, ftype, default in fields
        )

        code = self.TEMPLATES["python"]["dataclass"].format(
            name=name,
            docstring=description,
            fields=fields_str
        )

        return GeneratedCode(
            code=code.strip(),
            language="python",
            description=f"Generated dataclass: {name}",
            imports=["from dataclasses import dataclass"]
        )

    def add_custom_template(self, language: str, name: str, template: str) -> None:
        """Add a custom template."""
        if language not in self._custom_templates:
            self._custom_templates[language] = {}
        self._custom_templates[language][name] = template

    def list_templates(self, language: str = "python") -> list[str]:
        """List available templates for a language."""
        builtin = list(self.TEMPLATES.get(language, {}).keys())
        custom = list(self._custom_templates.get(language, {}).keys())
        return builtin + custom

    def list_patterns(self) -> list[str]:
        """List available design patterns."""
        return list(self.COMMON_PATTERNS.keys())
