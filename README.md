# NAME
`visual-python` - Visual REPL for Python (2D formula renderer and editor with syntax highlighting) (to be used
 together with sympy et al.)



# DESCRIPTION
`visual-python` is intended to be an universal terminal (text-based) formula editing tool. It generates 
`sympy`-compatible code ready to be `eval()`uated. 



# FEATURES
Status: **proof of concept**
- [x] baselines
- [x] syntax highlighting
- [x] code execution
- [ ] keybindings
- [ ] teleporting cursor to mouse click
- [ ] repl-like visual interface
- [ ] text selection
- [ ] copy/paste selection
- [ ] multiline statements

| Feature        | Codegen | Rendering | Inserting | Removing | Movement |
| :------------- | :-----: | :-------: | :-------: | :------: | :------: |
| Text           | yes     | yes       | yes       | yes      | yes      |
| Fraction       | yes     | yes       | yes       | yes      | sort of  |
| Parenthesis    | yes     | yes       | sort of   |          | yes      |
| Power          |         |           |           |          |          |
| Square root    |         |           |           |          |          |
| Matrix         |         |           |           |          |          |
| Sum, Lim, etc. |         |           |           |          |          |
| Invisible mult.| ?       | ?         | ?         | ?        | ?        |




# SETTINGS
- Syntax highlighting colors
- Fraction padding



# SEE ALSO
- [python](https://docs.python.org/3/)
- [sympy](https://docs.sympy.org/)
- [formulador](https://github.com/stylewarning/formulador)



# AUTHOR
Ondrej Telka, https://ondrej.xyz/

