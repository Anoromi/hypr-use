"""Candidate only: omit sampled-out cells only when emptiness was read successfully."""
def confirmed_empty_text_cell(is_text,character_count):
 return is_text is True and character_count==0

def retain_cell(*,empty,selected,focused,empty_seen,limit=12):
 return not empty or selected or focused or empty_seen<limit
