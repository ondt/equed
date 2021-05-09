# EquEd - Equation Editor
`equed` - WYSIWYG math editor for terminal with syntax highlighting.

<div align="center" style="display:inline;">
  <img src="https://user-images.githubusercontent.com/20520951/117576686-16b7a480-b0e7-11eb-8743-07606b9c377e.gif" width="49%">
  <img src="https://user-images.githubusercontent.com/20520951/117576620-dce69e00-b0e6-11eb-90f9-892009544b57.gif" width="49%">
</div>




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

