#!/usr/bin/python

import sys
import lxml.html
import subprocess

if len(sys.argv) < 2:
    print("File argument missing")
    quit()

filename = sys.argv[1]
s = subprocess.check_output(["pdftohtml", "-s", "-i", "-stdout", filename]).decode("utf-8")

ps = []
d = "<!DOCTYPE"
htmls = [lxml.html.fromstring(d + e) for e in s.split(d) if e]
for html in htmls:
    fields = html.cssselect("p")
    for field in fields:
        slanted = field.cssselect("i")
        if slanted:
            field = slanted[0]
        if field.text is not None and "£" in field.text and field.text.index("£") > 0:
            split = field.text.split("£")
            ps.append(split[0])
            ps.append("£" + split[1])
        else:
            ps.append(field.text)

items = []
substitutions = []
delivery = None
total = None
coupons = 0
acc = ""
for i in range(len(ps)):
    if ps[i] is not None:
        print(ps[i])
        if ps[i][:8] == "Subtotal":
            delivery = float(ps[i - 1][1:])
            total = float(ps[i + 1][1:])
            if ps[i + 2] == "Coupons":
                coupons = float(ps[i + 3][2:])
            break
        elif ps[i][0] == "£" and ps[i - 1] is not None:
            if ps[i + 1] is None or ps[i + 1][:11] != "substituted":
                price = float(ps[i][1:])
                split = acc.split("\xa0")
                if split[0] == "substituted":
                    number = int(split[2])
                    name = " ".join(split[3:])
                    old_price = float(ps[i - 2][1:])
                    split = ps[i - 3].split("\xa0")
                    old_number = int(split[0])
                    old_name = " ".join(split[1:])
                    substitutions.append((old_number, old_name, old_price, number, name, price))
                else:
                    try:
                        number = int(split[0])
                    except:
                        number = 1
                    name = " ".join(split[1:])
                    items.append((number, name, price))
            acc = ""
        else:
            if ps[i] is not None and ps[i][0] != "(":
                if acc != "":
                    acc += " "
                acc += ps[i]

print()
print("overview:")
for number, name, price in items:
    print(name + " (" + str(number) + ", £" + str(price) + ")")
print()

print("substitutions:")
for old_number, old_name, old_price, number, name, price in substitutions:
    print(old_name + " (" + str(old_number) + ", £" + str(old_price) + ") -> " + name + " (" + str(number) + ", £" + str(price) + ")")
print()

item_total = 0
for item in items:
    item_total += item[2]
item_total = round(item_total, 2)
check = item_total + delivery
if check != total:
    print("items + delivery != total: " + str(check) + " vs " + str(total))
    quit()
print("sum " + str(item_total))
print("delivery " + str(delivery))
print("total " + str(total))
print()
input("enter to continue")

usernames = []
user_search = {}
f = open("users", "r")
lines = f.readlines()
f.close()
user = None
for line in lines:
    line = line.strip()
    if line == "":
        user = None
    elif user is None:
        user = line
        usernames.append(user)
        user_search[user] = []
    else:
        user_search[user].append(line)
print(usernames)

def get_contribution(try_auto, item, provided = None):
    number, name, price = item
    lowered = name.lower()
    auto = 0
    dist = None
    if try_auto:
        for user in usernames:
            for keyword in user_search[user]:
                keyword = keyword.lower()
                level = 1
                if keyword[0] == "!":
                    keyword = keyword[1:]
                    level = 2
                if keyword in lowered:
                    index = lowered.index(keyword)
                    if (index == 0 or not lowered[index - 1].isalpha()) and (len(keyword) == len(lowered) - index or not lowered[index + len(keyword)].isalpha()):
                        dist = [user]
                        auto = level
                        if auto == 2:
                            break
            if auto == 2:
                break
        if auto == 2:
            for _, _, _, _, substituted_name, _ in substitutions:
                if substituted_name == name:
                    auto = 1
                    break
    if dist is None:
        print()
        print(name)
        print("Number: " + str(number))
        print("Price: " + str(price))
        if provided is None:
            dist = input("> ").split(" ")
        else:
            dist = provided
    if not dist or (len(dist) == 1 and dist[0] == ""):
        dist = ["1"] * len(usernames)
    if len(dist) == 1 and len(dist[0]) > 0:
        for j, user in enumerate(usernames):
            if dist[0].lower() == user[:len(dist[0])].lower():
                dist = ["0"] * j + ["1"]
                break
    user_contribution = {}
    for user in usernames:
        user_contribution[user] = 0
    total = 0
    for j, x in enumerate(dist):
        x = float(x)
        total += x
        user_contribution[usernames[j]] = x
    if total != 0:
        for user in usernames:
            user_contribution[user] *= price / total
            if user_contribution[user] != 0 and auto == 0:
                print("Adding " + str(user_contribution[user]) + " for " + str(user))
    return auto, user_contribution

contributions = []
autos = []
for item in items:
    auto, user_contribution = get_contribution(True, item)
    autos.append(auto)
    contributions.append(user_contribution)
change = True
while change:
    print()
    print("Auto distributions to review:")
    indices = {}
    index = 1
    for i in range(len(autos)):
        if autos[i] == 1:
            indices[index] = i
            minimised = contributions[i].copy()
            for user in list(minimised.keys()):
                if minimised[user] == 0:
                    del minimised[user]
            print("#" + str(index) + ": " + items[i][1] + " (" + str(items[i][0]) + ", £" + str(items[i][2]) + ")")
            print("    " + str(minimised))
            index += 1
    print()
    response = input("Change any auto distributions? ").split(" ")
    if response[0].isdigit():
        n = indices[int(response[0])]
        provided = None
        if len(response) > 1:
            provided = response[1:]
        _, contributions[n] = get_contribution(False, items[n], provided)
        autos[n] = 0
    else:
        change = False
print()
print("Unreviewed auto distributions:")
for i in range(len(autos)):
    if autos[i] == 2:
        minimised = contributions[i].copy()
        for user in list(minimised.keys()):
            if minimised[user] == 0:
                del minimised[user]
        print(items[i][1] + " (" + str(items[i][0]) + ") " + str(minimised))
user_total = {}
for user in usernames:
    user_total[user] = 0
for user_contribution in contributions:
    for user in usernames:
        user_total[user] += user_contribution[user]
print()
for user in usernames:
    print("Adding " + str(delivery / len(usernames)) + " delivery for " + str(user))
    user_total[user] = round(user_total[user] + delivery / len(usernames), 2)
print()
print(user_total)
print("distributed " + str(sum(user_total.values())) + ", total " + str(total))
if coupons > 0:
    print("Note: unaccounted " + str(coupons) + " coupon discount")
