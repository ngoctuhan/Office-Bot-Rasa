current_action = "action_ask_location_2"
next_action_accept = "action_confirm_location_2"
next_action_reject = "action_fallback_operator_location"

entities = ["number", "ngach", "ngo", "street", "district", "county"]
output_file_name = "output/intent_gen.txt"


def bit_field(n):
    return [int(digit) for digit in bin(n)[2:]]


if __name__ == "__main__":
    first = "> " + current_action + " > show_location{"
    maximum_examples = int(pow(2, len(entities)))
    fo = open(output_file_name, "w")
    for field in range(maximum_examples):
        bits = bit_field(maximum_examples - 1 - field)
        intent = ""
        x = [0] * (len(entities) - len(bits))
        x.extend(bits)
        bits = x
        for i, b in enumerate(bits):
            if b == 1:
                intent += '"{}":"1", '.format(entities[i])
        if len(intent) > 1:
            intent = intent[:-2]
        last = "} > " + next_action_reject
        if (bits[0] == 1 or bits[1] == 1 or bits[2] == 1) \
                and (bits[3] == 1 or bits[4] == 1 or bits[5] == 1):
            last = "} > " + next_action_accept
        print("{}{}{}".format(first, intent, last), file=fo)
