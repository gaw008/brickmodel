# Initial failing test evidence

The original pytest XML is preserved byte-for-byte in energy-state-identity-initial-red.raw.zip (member energy-state-identity-initial-red.xml). Its SHA256 is 8c5e5910f6dbe168a7aaba473af35640efc7d9be1356d27b7cba61ac91b0230f.

The adjacent .xml is a whitespace-normalized review copy: only trailing ASCII space/tab bytes on each line were removed, because git diff --cached --check rejected two traceback lines. Test status, assertions, counts and original failure evidence remain unchanged. The raw archive was read back and byte-compared before writing this review copy.
