import json
from pathlib import Path
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib
GLib.set_prgname("hypr-a11y-fixture")
GLib.set_application_name("A11y fixture")
p=Path(__file__).resolve().parent/'a11y-experiments/fixture-state.json'
state={'clicks':0,'format':'Text CSV'}
def save():p.write_text(json.dumps(state))
w=Gtk.Window(title='A11y experiment');w.set_default_size(600,350)
b=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);w.add(b)
c=Gtk.ComboBoxText();c.append_text('Text CSV');c.append_text('ODF Spreadsheet');c.set_active(0);b.pack_start(c,False,False,0)
def changed(*a):state['format']=c.get_active_text();save()
c.connect('changed',changed)
scroll=Gtk.ScrolledWindow();b.pack_start(scroll,True,True,0)
inner=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);scroll.add(inner)
spacer=Gtk.Label(label='Scrollable content');spacer.set_size_request(300,50);inner.pack_start(spacer,False,False,0)
button=Gtk.Button(label='Record offscreen action');inner.pack_start(button,False,False,0)
def clicked(*a):state['clicks']+=1;save()
button.connect('clicked',clicked);w.connect('destroy',Gtk.main_quit);w.show_all();save();Gtk.main()
