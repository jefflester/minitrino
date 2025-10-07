I'll examine the config command file to understand how the decorators work with Click's command and options parsing.

Let me examine the utils module to understand how the decorators work with Click's command and options parsing.

Looking at your decorator stack, there are several ways decorators can access the incoming command and Click options:

## 1. **Click Context Access**
Click provides a context object that contains parsed command information:

```python
import click
from functools import wraps

def my_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get the current Click context
        ctx = click.get_current_context()
        
        # Access command info
        command_name = ctx.info_name  # "config"
        params = ctx.params           # {"reset": True/False}
        
        # You can also access the raw command line args
        raw_args = ctx.parent.params if ctx.parent else {}
        
        print(f"Command: {command_name}")
        print(f"Options: {params}")
        
        return func(*args, **kwargs)
    return wrapper
```

## 2. **Function Signature Inspection** (like your [exception_handler](cci:1://file:///Users/jlester/work/repos/minitrino/src/cli/minitrino/utils.py:110:0-143:18))
Your current [exception_handler](cci:1://file:///Users/jlester/work/repos/minitrino/src/cli/minitrino/utils.py:110:0-143:18) already demonstrates this pattern:

```python
def exception_handler(func: Any) -> Any:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        sig = signature(func)
        
        # Parse out the ctx parameter by name
        ctx = None
        if "ctx" in sig.parameters:
            ctx = kwargs.get("ctx")
            # ... or find it in positional args
        
        # Access other parameters by name
        reset_value = kwargs.get("reset", False)
        
        return func(*args, **kwargs)
    return wrapper
```

## 3. **Enhanced Decorator with Click Integration**
Here's how you could create a decorator that captures both command info and parsed options:

```python
def telemetrize():
    def decorator(func):
        @wraps(func) 
        def wrapper(*args, **kwargs):
            # Get Click context for command info
            click_ctx = click.get_current_context()
            command_name = click_ctx.info_name
            
            # Get parsed options from kwargs
            parsed_options = {
                key: value for key, value in kwargs.items() 
                if key != 'ctx'  # Exclude the MinitrinoContext
            }
            
            # Get the MinitrinoContext from args/kwargs
            sig = signature(func)
            ctx = None
            if "ctx" in sig.parameters:
                ctx = kwargs.get("ctx")
                if ctx is None and args:
                    ctx_index = list(sig.parameters).index("ctx")
                    if len(args) > ctx_index:
                        ctx = args[ctx_index]
            
            # Now you have:
            # - command_name: "config" 
            # - parsed_options: {"reset": True/False}
            # - ctx: MinitrinoContext instance
            
            # Do your telemetry logic here
            if ctx and hasattr(ctx, 'logger'):
                ctx.logger.debug(f"Executing command: {command_name} with options: {parsed_options}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

## 4. **Accessing Click's Raw Arguments**
If you need access to the original command line arguments:

```python
def command_inspector(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        click_ctx = click.get_current_context()
        
        # Get the original command line tokens
        if hasattr(click_ctx, 'protected_args'):
            raw_args = click_ctx.protected_args
        
        # Get all Click parameters (includes defaults)
        all_params = click_ctx.params
        
        # Get only the parameters that were actually provided
        provided_params = {
            param.name: click_ctx.params[param.name] 
            for param in click_ctx.command.params 
            if param.name in click_ctx.params
        }
        
        return func(*args, **kwargs)
    return wrapper
```

## Key Points:

1. **Decorator Order Matters**: Click decorators (`@click.command`, `@click.option`) must be closest to the function since they modify the function signature.

2. **Context Availability**: `click.get_current_context()` is only available during command execution, not during decoration time.

3. **Your Current Pattern**: Your [@utils.pass_environment()](cci:1://file:///Users/jlester/work/repos/minitrino/src/cli/minitrino/utils.py:32:0-43:61) uses Click's `make_pass_decorator()`, which is the recommended way to inject dependencies while preserving Click's parameter parsing.

In your telemetry decorator, you'd want to use `click.get_current_context()` to access the command name and `kwargs` inspection to get the parsed option values.