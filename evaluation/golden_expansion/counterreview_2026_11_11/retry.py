"""One bounded retry for four incomplete/invalid outputs. No prior AI output supplied."""
import run
FAILED=['GC-003','GC-012','SP-013','SP-014']
EXTRA='''IMPORTANT: Do NOT echo the input JSON. Produce only the requested review object. Quotes must be SHORT (under 160 characters) exact substrings of STRING LEAVES, never serialized objects. Use zero-based array indices. For example /writing_contract/required_information/0/description points to a string, while /writing_contract/required_information/0 is an object and INVALID. If no candidate content is available, cite its availability string and the missing_context string instead. Do not invent missing text. Keep the total response under 1200 tokens.\n'''
if __name__=='__main__':
 rows=[r for r in run.inputs() if r['case_id'] in FAILED]
 run.inputs=lambda:rows
 run.PROMPT+=EXTRA
 run.OUT=run.OUT/'retry-01';run.OUT.mkdir(exist_ok=True)
 run.main()
