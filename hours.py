import subprocess, datetime
from collections import defaultdict

commits = subprocess.check_output(
        "git log --date=iso | grep -A 1 kent | grep Date | sed 's/Date: \\+//'",
        shell=True).strip().split(b"\n")
commits = [datetime.datetime.fromisoformat(i.decode()) for i in commits]

days = defaultdict(list)
for commit in commits:
    days[(commit.year, commit.month, commit.day)].append(commit)

days = sorted([
        (date, (max(times) - min(times)).total_seconds() / 3600)
        for date, times in days.items() if len(times) > 1])
print("Date        Hours")
print("\n".join(f"{y}/{m:02}/{d:02}: {t: 4.2f}" for (y, m, d), t in days))
print("            -----")

total = sum(list(zip(*days))[1])
rate = 20
print(f"{total: 17.2f} * {rate} = ${total * rate:.2f}")
print("https://www.paloalto.gov/Business/Business-Resources/Minimum-Wage")

