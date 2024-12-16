from _curses import window

version: str

class _Curses_Panel:  # type is <class '_curses_panel.curses panel'> (note the space in the class name)
    def above(self) -> _Curses_Panel: ...
    def below(self) -> _Curses_Panel: ...
    def bottom(self) -> None: ...
    def hidden(self) -> bool: ...
    def hide(self) -> None: ...
    def move(self, y: int, x: int) -> None: ...
    def replace(self, win: window) -> None: ...
    def set_userptr(self, obj: object) -> None: ...
    def show(self) -> None: ...
    def top(self) -> None: ...
    def userptr(self) -> object: ...
    def window(self) -> window: ...

def bottom_panel() -> _Curses_Panel:
    """Return the bottom panel in the panel stack."""
    ...
def new_panel(win: window, /) -> _Curses_Panel:
    """Return a panel object, associating it with the given window win."""
    ...
def top_panel() -> _Curses_Panel:
    """Return the top panel in the panel stack."""
    ...
def update_panels() -> _Curses_Panel:
    """
    Updates the virtual screen after changes in the panel stack.

    This does not call curses.doupdate(), so you'll have to do this yourself.
    """
    ...