import gi,json,sys,signal
from pathlib import Path
gi.require_version('Gtk','3.0');from gi.repository import Gtk,GLib
GLib.set_prgname('hypr-use-bench');GLib.set_application_name('Hypr-use Benchmark')
root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True);state={};win=Gtk.Window(title='Hypr-use Benchmark');win.set_default_size(750,650)
box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);win.add(box)
def save(*args):(root/'state.json').write_text(json.dumps(state))
def label(t):box.pack_start(Gtk.Label(label=t),False,False,0)
def entry(name):
 label(name);w=Gtk.Entry();w.get_accessible().set_name(name);box.pack_start(w,False,False,0);w.connect('changed',lambda w:(state.update({name:w.get_text()}),save()));return w
name=entry('Name');email=entry('Email');note=entry('Note')
check=Gtk.CheckButton(label='Newsletter');box.pack_start(check,False,False,0);check.connect('toggled',lambda w:(state.update(Newsletter=w.get_active()),save()))
combo=Gtk.ComboBoxText();combo.get_accessible().set_name('Country')
for v in ['Japan','United States','Germany']:combo.append_text(v)
combo.set_active(0);box.pack_start(combo,False,False,0);combo.connect('changed',lambda w:(state.update(Country=w.get_active_text()),save()))
status=Gtk.Label(label='Ready');box.pack_start(status,False,False,0)
def button(title,fn):
 b=Gtk.Button(label=title);box.pack_start(b,False,False,0);b.connect('clicked',fn)
def write(*a):
 (root/'note.txt').write_text(note.get_text());state['saved_note']=note.get_text();status.set_text('Note saved');save()
def read(*a):note.set_text((root/'note.txt').read_text() if (root/'note.txt').exists() else '');status.set_text('Note reopened')
def files(*a):
 folder=root/name.get_text()
 if folder.parent!=root or not name.get_text():return
 folder.mkdir(exist_ok=True);state['folder']=name.get_text();status.set_text('Folder created');save()
def dialog(*a):
 delay=int(sys.argv[2]) if len(sys.argv)>2 else 0
 if delay:
  GLib.timeout_add(delay,lambda:(show_dialog(),False)[1]);return
 show_dialog()
def show_dialog():
 d=Gtk.Dialog(title='Benchmark confirmation',transient_for=win,modal=True);d.add_button('Confirm',Gtk.ResponseType.OK);d.add_button('Cancel',Gtk.ResponseType.CANCEL)
 def response(d,r):state['dialog_result']='confirmed' if r==Gtk.ResponseType.OK else 'cancelled';save();d.destroy()
 d.connect('response',response);d.show_all()
button('Save note',write);button('Reopen note',read);button('Create folder named above',files);button('Open confirmation',dialog)
win.connect('destroy',Gtk.main_quit);GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGTERM,lambda:(Gtk.main_quit(),False)[1]);win.show_all();name.grab_focus();save();Gtk.main()
