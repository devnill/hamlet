from hamlet.gui.kitty.protocol import detect_kitty_support

KITTY_AVAILABLE: bool = detect_kitty_support()

__all__ = ["KITTY_AVAILABLE"]
