import faulthandler, sys
faulthandler.enable(file=sys.stderr)
from hamlet.gui.notcurses.app import NotcursesApp
app = NotcursesApp('http://localhost:8080')
# Auto-quit via a timer thread
import threading
def quit_later():
    import time; time.sleep(5)
    app._running = False
threading.Thread(target=quit_later, daemon=True).start()
code = app.run()
print(f'clean exit: {code}', file=sys.stderr)