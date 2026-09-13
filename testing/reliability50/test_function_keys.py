"""Compile the production key parser and compare it with Linux's key constants."""
from pathlib import Path
import subprocess,tempfile
source=Path(__file__).resolve().parents[2]/'vendor/hypr-agent-portal-0.56.2/src/plugin/main.cpp'
s=source.read_text()
def extract(signature):
 start=s.index(signature);end=s.index('\n}',start)+2;return s[start:end]
code='''#include <linux/input-event-codes.h>
#include <string>
#include <string_view>
#include <optional>
#include <unordered_map>
#include <charconv>
#include <algorithm>
#include <array>
#include <iostream>
'''+ '\n'.join(extract(n) for n in ['std::string trim(','std::string lower(','std::optional<uint32_t> keyboardKey('])+'''
int main(){
 const unsigned expected[]={KEY_F1,KEY_F2,KEY_F3,KEY_F4,KEY_F5,KEY_F6,KEY_F7,KEY_F8,KEY_F9,KEY_F10,KEY_F11,KEY_F12};
 bool ok=true;
 for(unsigned i=0;i<12;++i){auto got=keyboardKey("F"+std::to_string(i+1));if(got!=expected[i]){std::cout<<"F"<<i+1<<" got "<<got.value_or(999)<<" expected "<<expected[i]<<"\\n";ok=false;}}
 if(keyboardKey("1")!=KEY_1 || keyboardKey("0")!=KEY_0 || keyboardKey("88")!=KEY_F12 || keyboardKey("F0"))ok=false;
 return ok?0:1;
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.cpp').write_text(code)
 subprocess.run(['c++','-std=c++23',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('Production function-key parser passed F1-F12 and numeric-key checks.')
