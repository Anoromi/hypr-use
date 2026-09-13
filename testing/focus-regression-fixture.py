import gi,json,sys,signal
from pathlib import Path
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib
GLib.set_prgname('hypr-use-focus-test');GLib.set_application_name('hypr-use-focus-test')
p=Path(sys.argv[1]);state={'text':'','popup_open':False};w=Gtk.Window(title='Background focus regression');w.set_default_size(500,240)
b=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);w.add(b);entry=Gtk.Entry();b.pack_start(entry,False,False,0)
button=Gtk.Button(label='Open test dialog');b.pack_start(button,False,False,0)
def save():p.write_text(json.dumps(state))
def changed(*a):state['text']=entry.get_text();save()
def popup(*a):
 d=Gtk.Dialog(title='Background test dialog',transient_for=w,modal=True);d.add_button('Close test dialog',Gtk.ResponseType.CLOSE);d.connect('response',lambda *a:d.destroy());d.connect('destroy',lambda *a:closed());state['popup_open']=True;save();d.show_all()
def closed():state['popup_open']=False;save()
entry.connect('changed',changed);button.connect('clicked',popup);w.connect('destroy',Gtk.main_quit)
GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGTERM,lambda:(Gtk.main_quit(),False)[1]);w.show_all();entry.grab_focus();save();Gtk.main()
