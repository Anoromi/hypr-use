#include "keymap_resolver.hpp"
#include <cassert>
#include <linux/input-event-codes.h>
#include <cstdio>
int main() {
 auto* ctx=xkb_context_new(XKB_CONTEXT_NO_FLAGS);
 xkb_rule_names n{}; n.layout="us,us,ua,ru"; n.variant="dvorak,,,";
 auto* map=xkb_keymap_new_from_names(ctx,&n,XKB_KEYMAP_COMPILE_NO_FLAGS); assert(map);
 auto t=resolvePortalKey(map,KEY_T,4,0);assert(t && t->key==KEY_K && t->group==0);
 auto q=resolvePortalKey(map,KEY_T,4,1);assert(q && q->key==KEY_T && q->group==1);
 for (auto key : {KEY_H,KEY_T,KEY_P,KEY_S,KEY_SEMICOLON,KEY_SLASH,KEY_G,KEY_O,KEY_L,KEY_E,KEY_DOT,KEY_C,KEY_M,KEY_ENTER}) {
   auto r=resolvePortalKey(map,key,0,0);assert(r);
 }
 auto colon=resolvePortalKey(map,KEY_SEMICOLON,1,0);assert(colon && colon->key==KEY_Z);
 auto fallback=resolvePortalKey(map,KEY_T,4,3);assert(fallback && fallback->group==0);
 xkb_keymap_unref(map);xkb_context_unref(ctx);puts("Dvorak, QWERTY, punctuation, Return and Cyrillic fallback passed");
}
