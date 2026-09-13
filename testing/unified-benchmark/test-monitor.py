import threading
from monitor import Monitor
m=Monitor.__new__(Monitor);m.classes={'soffice','libreoffice-calc'};m.targets=set();m.active='0xuser';m.stage='test';m.trigger=threading.Event();m.violations=[];m.record=lambda *args:None;m.callback=lambda:None
m.handle_event('openwindow','abc,902,soffice,Import')
assert '0xabc' in m.targets
m.handle_event('closewindow','abc')
assert '0xabc' not in m.targets
m.handle_event('openwindow','abc,2,hyprnav-browser-dev,Zen')
m.handle_event('activewindowv2','abc')
assert not m.trigger.is_set()
# Even a missing close event must not retain a reused address.
m.targets.add('0xdef');m.handle_event('openwindow','def,2,unrelated,Editor');m.handle_event('activewindowv2','def')
assert not m.trigger.is_set()
m.handle_event('openwindow','fed,902,libreoffice-calc,Sheet');m.handle_event('activewindowv2','fed')
assert m.trigger.is_set() and len(m.violations)==1
print('Address reuse is ignored; real target activation still stops the run.')
