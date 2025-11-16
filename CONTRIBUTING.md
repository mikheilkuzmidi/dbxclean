# Contributing to Dropbox Sorter

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

1. Follow the installation instructions in [SETUP.md](SETUP.md)
2. Create a new branch for your feature/fix
3. Make your changes
4. Test your changes
5. Submit a pull request

## Code Style

### Python (Backend)
- Follow PEP 8 style guide
- Use type hints where appropriate
- Add docstrings to all public functions/classes
- Keep functions focused and small
- Use meaningful variable names

### JavaScript/React (Frontend)
- Use functional components with hooks
- Follow React best practices
- Use meaningful component and variable names
- Keep components small and focused
- Add comments for complex logic

## Project Structure

```
dropbox-sorter/
├── backend/
│   ├── app/
│   │   ├── analyzers/      # Analysis modules
│   │   ├── main.py         # FastAPI app
│   │   ├── models.py       # Database models
│   │   ├── config.py       # Configuration
│   │   ├── database.py     # Database setup
│   │   ├── dropbox_client.py  # Dropbox API client
│   │   ├── validators.py   # Input validation
│   │   └── logging_config.py  # Logging setup
│   ├── scripts/            # Utility scripts
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/          # Page components
│   │   ├── App.jsx         # Main app component
│   │   └── api.js          # API client
│   └── package.json        # Node dependencies
└── docs/                   # Documentation
```

## Adding New Features

### Backend API Endpoints

1. Add the endpoint in `backend/app/main.py`
2. Add input validation using Pydantic models
3. Use the `@app.get()` or `@app.post()` decorators
4. Add proper error handling
5. Update API documentation

Example:
```python
@app.get("/api/my-endpoint")
def my_endpoint(
    param: str,
    db: Session = Depends(get_db)
):
    """My endpoint description"""
    try:
        # Implementation
        return {"result": "success"}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Frontend Components

1. Create new component in `frontend/src/pages/` or `frontend/src/components/`
2. Use functional components
3. Add to routing in `App.jsx` if it's a page
4. Follow existing styling patterns

Example:
```jsx
import React, { useState, useEffect } from 'react';

function MyComponent() {
  const [data, setData] = useState(null);

  useEffect(() => {
    // Load data
  }, []);

  return (
    <div>
      {/* Component content */}
    </div>
  );
}

export default MyComponent;
```

### Analyzers

To add a new analyzer:

1. Create a new file in `backend/app/analyzers/`
2. Implement your analysis class
3. Add it to the scan job in `main.py`

Example:
```python
class MyAnalyzer:
    """Analyzer description"""

    def __init__(self, db: Session):
        self.db = db

    def analyze(self, files: List[FileMetadata]) -> Dict:
        """Perform analysis"""
        # Implementation
        return results
```

## Testing

### Backend Testing

```bash
cd backend
source venv/bin/activate

# Run tests (when implemented)
pytest

# Type checking
mypy app/

# Linting
flake8 app/
```

### Frontend Testing

```bash
cd frontend

# Run tests (when implemented)
npm test

# Linting
npm run lint

# Type checking (if using TypeScript)
npm run type-check
```

## Documentation

- Update README.md for user-facing changes
- Update SETUP.md for installation/configuration changes
- Add inline comments for complex logic
- Update API documentation
- Add docstrings to all functions/classes

## Pull Request Process

1. **Create a branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make your changes**
   - Write clean, documented code
   - Follow project code style
   - Add tests if applicable

3. **Test your changes**
   ```bash
   make verify
   # Test manually
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add my feature"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```

6. **PR Description**
   - Describe what changes you made
   - Why the changes are needed
   - How to test the changes
   - Screenshots if UI changes

## Code Review Guidelines

When reviewing PRs:
- Check code quality and style
- Verify functionality works
- Look for security issues
- Ensure documentation is updated
- Test the changes locally

## Security

- Never commit `.env` files
- Never commit API keys or tokens
- Always validate user input
- Use parameterized queries
- Follow security best practices

## Questions?

If you have questions:
- Check existing documentation
- Look at existing code for examples
- Open an issue for discussion

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
