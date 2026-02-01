# AI Code Review for Azure DevOps

Automatically review Pull Requests using OpenAI's GPT models. Get instant feedback on security vulnerabilities, performance issues, and best practices.

![AI Code Review](images/screenshot-pr-comment.png)

## Features

- **Automated PR Reviews** - Runs automatically on every Pull Request
- **Multi-Language Support** - Python, JavaScript/TypeScript, C#, Java, Go, Rust, C++, and more
- **Framework-Aware** - React, Vue, Angular, FastAPI, Flask, Express, Spring, ASP.NET
- **Security Analysis** - OWASP Top 10, injection vulnerabilities, authentication issues
- **Performance Review** - Algorithm complexity, database queries, memory management
- **Inline Comments** - Posts comments directly on problematic lines
- **Configurable** - Choose model, file limits, and more

## Quick Start

### 1. Install the Extension

Install from the [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=your-publisher-id.ai-code-review).

### 2. Add to Your Pipeline

```yaml
trigger: none

pr:
  branches:
    include:
      - main
      - develop

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: AICodeReview@1
  inputs:
    openaiApiKey: $(OPENAI_API_KEY)
    openaiModel: 'gpt-5.2-codex'
```

### 3. Configure API Key

Add `OPENAI_API_KEY` as a secret variable in your pipeline or variable group.

### 4. Enable OAuth Token

In your pipeline settings, ensure **"Allow scripts to access the OAuth token"** is enabled, or add:

```yaml
steps:
- task: AICodeReview@1
  inputs:
    openaiApiKey: $(OPENAI_API_KEY)
  env:
    SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

## Configuration Options

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `openaiApiKey` | Yes | - | Your OpenAI API key |
| `openaiModel` | No | `gpt-5.2-codex` | Model to use for review |
| `maxFiles` | No | `50` | Max files to review per PR |
| `maxLinesPerFile` | No | `1000` | Truncate files larger than this |
| `debug` | No | `false` | Enable verbose logging |
| `continueOnError` | No | `true` | Don't fail pipeline on review error |

## Supported Languages

| Language | Review Coverage |
|----------|----------------|
| Python | PEP 8, type hints, async patterns, testing |
| JavaScript/TypeScript | Modern ES, async/await, error handling |
| C#/.NET | LINQ, async/await, null safety, DI |
| Java | Streams, Optional, Spring patterns |
| Go | Error handling, concurrency, interfaces |
| Rust | Ownership, error handling, unsafe code |
| C/C++ | Memory management, RAII, modern C++ |

## Supported Frameworks

| Framework | Review Coverage |
|-----------|----------------|
| React | Hooks, performance, accessibility |
| Vue | Composition API, reactivity, Pinia |
| Angular | Signals, standalone components, RxJS |
| FastAPI | Async, Pydantic, dependency injection |
| Flask | Blueprints, error handling |
| Express | Middleware, error handling, security |
| Spring Boot | DI, transactions, JPA |
| ASP.NET Core | DI, async, minimal APIs |

## Review Categories

### Critical (Blocking)
- Security vulnerabilities (OWASP Top 10)
- Data integrity risks
- Breaking changes

### High Priority
- Logic errors
- Null handling issues
- Error handling problems
- Resource leaks

### Suggestions
- Performance improvements
- Code quality enhancements
- Best practice recommendations

## Example Output

The task posts a comprehensive review comment on your PR:

```markdown
## Code Review Summary

**Overall Assessment**: REQUEST CHANGES

### Critical Issues (Blocking)

#### 1. SQL Injection Vulnerability
- **File**: `src/repository.py:45`
- **Problem**: String concatenation in SQL query
- **Solution**: Use parameterized queries

### Suggestions

#### 1. Consider using async/await
- **File**: `src/service.py:23`
- **Current**: Synchronous database calls
- **Suggested**: Use async for better performance
```

## Privacy & Security

- Your code is sent to OpenAI's API for analysis
- API key is handled as a secret and never logged
- No code is stored by this extension
- Review results are posted only to your PR

## Support

- [GitHub Issues](https://github.com/your-username/ai-code-review-extension/issues)
- [Documentation](https://github.com/your-username/ai-code-review-extension)

## License

MIT License - See [LICENSE](LICENSE) for details.
