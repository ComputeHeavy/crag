# Code Retrieval Augmented Generation

This is a utility to help you fetch code snippets for injecting into prompts. Currently works with Python.

* Function from file
* Class from file
* Function from class from file
* Summarize class

```bash
python main.py fetch --file FILE.py --function FUNCTION_NAME
python main.py fetch --file FILE.py --class CLASS_NAME
python main.py fetch --file FILE.py --class CLASS_NAME --function FUNCTION_NAME
python main.py summarize --file FILE.py --class CLASS_NAME 
```

## Future

* Use `function_info()` to summarize a single function
* Summarize an entire file
* Add a token counting interface to estimate context window usage