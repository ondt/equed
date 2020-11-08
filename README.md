# NAME
`visual-python` - Visual REPL for Python (2D formula renderer and editor with syntax highlighting) (to be used
 together with sympy, etc)



# DESCRIPTION
`visual-python` is intended to be an universal terminal (text-based) formula editing tool. It generates 
`sympy`-compatible code ready to be `eval()`uated. 



# FEATURES
Status: **proof of concept (the editing works!)**
- [x] baselines
- [x] syntax highlighting
- [x] code execution
- [ ] keybindings
- [ ] teleporting cursor to mouse click
- [ ] better wrapping
- [ ] repl-like visual interface
- [ ] text selection
- [ ] copy/paste selection
- [ ] multiline statements

| Feature        | Codegen | Rendering | Inserting | Removing | Movement |
| :------------- | :-----: | :-------: | :-------: | :------: | :------: |
| Text           | yes     | yes       | yes       | yes      | yes      |
| Fraction       | yes     | yes       | yes       | yes      | sort of  |
| Parenthesis    | yes     | yes       | yes       | yes      | yes      |
| Power          |         |           |           |          |          |
| Square root    |         |           |           |          |          |
| Matrix         |         |           |           |          |          |
| Sum, Lim, etc. |         |           |           |          |          |
| Invisible mult.| ?       | ?         | ?         | ?        | ?        |




# SETTINGS
- **Editing**
    - Skip fraction denominator when pressing RIGHT
    - Maple fraction DEL
    - Fraction inserting method (maple, split, empty)
- **Rendering**
    - Fraction padding
    - Fraction shorter line ends
    - Virtual cursor
- **Syntax highlighting colors**
    - Number
    - Text
    - Operator
    - Function
    - Fraction
    - Parenthesis
    - Unmatched parenthesis



# SEE ALSO
- [Maple](https://en.wikipedia.org/wiki/Maple_(software))
- [MathQuill](http://mathquill.com/)
- [Formulador](https://github.com/stylewarning/formulador)



# AUTHOR
Ondrej Telka, https://ondrej.xyz/

