import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk
w=Gtk.Window(title='hypr-use focus sentinel');w.set_default_size(400,300)
w.add(Gtk.Entry(placeholder_text='This foreground window must stay untouched'))
w.connect('destroy',Gtk.main_quit);w.show_all();Gtk.main()
