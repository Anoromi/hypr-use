import json
from pathlib import Path
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk
state=Path(__file__).resolve().parent/'session/fixture-state.json'
w=Gtk.Window(title='hypr-use test fixture');w.set_default_size(600,350)
b=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20);b.set_border_width(30);w.add(b)
b.pack_start(Gtk.Label(label='Disposable background input test'),False,False,0)
e=Gtk.Entry();e.set_placeholder_text('Type portal test here');b.pack_start(e,False,False,0)
button=Gtk.Button(label='Record value');b.pack_start(button,False,False,0)
status=Gtk.Label(label='Waiting');b.pack_start(status,False,False,0)
def save(confirmed=False):
    state.write_text(json.dumps({'text':e.get_text(),'confirmed':confirmed}))
def confirm(*args):save(True);status.set_text('Recorded: '+e.get_text())
e.connect('changed',lambda *_:save());button.connect('clicked',confirm)
w.connect('destroy',Gtk.main_quit);w.show_all();save();Gtk.main()
