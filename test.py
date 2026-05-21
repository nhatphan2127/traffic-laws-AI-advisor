import os
import re

string = """
Họ tên: Nguyễn Văn A
Email: nguyenvana@gmail.com
Email phụ: test_user-123@company.edu.vn

Số điện thoại:
- 0901234567
- +84 912-345-678
- (028) 3822 9999

Website:
https://openai.com
http://example.org/page?id=12
www.test-site.net

Ngày tháng:
17/05/2026
2026-05-17
May 17, 2026

Giá sản phẩm:
Laptop: $1200
Chuột: 350.000đ
Bàn phím: 1,250,000 VND

Địa chỉ IP:
192.168.1.1
8.8.8.8

Mã sản phẩm:
SP-12345
ID_9988
PROD-A1B2

Hashtag:
#python
#RegexLearning
#100DaysOfCode

Log hệ thống:
[2026-05-17 10:15:22] INFO - Server started
[2026-05-17 10:16:01] ERROR - Database connection failed
[2026-05-17 10:17:45] WARNING - Disk usage high

HTML:
<div class="container">
    <h1>Hello Regex</h1>
    <a href="https://google.com">Google</a>
</div>

Khoảng trắng test:
hello     world
python\tregex
line1

line2

Số:
123
-45
3.14159
1,000,000

Username:
user_01
admin123
test-user

File:
report.pdf
image.png
archive.tar.gz

Chuỗi đặc biệt:
abc123xyz
AA-999-BB
___hello___
"""

import re

text = """
Contact:
john@gmail.com
admin@company.local
support@yahoo.com
dev@test.internal
hello@openai.com
"""

text = """
Products:
$120
€99.5
VND 150000
USD 45.99
"""


result = re.findall(r"([$€]|\w+)\s?([0-9.]+)", text)
print(result)