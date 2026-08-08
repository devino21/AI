#!/usr/bin/env python3
"""Mock llama-server OpenAI endpoint for testing fleetbench end-to-end.
Behaves like a decent-but-imperfect model so scores land in the middle."""
import json, re
from http.server import BaseHTTPRequestHandler, HTTPServer

GOOD_CODE = {
    "compress": "```python\ndef compress(s):\n    if not s: return ''\n    out=[]; cur=s[0]; n=1\n    for ch in s[1:]:\n        if ch==cur: n+=1\n        else: out.append(cur+str(n)); cur=ch; n=1\n    out.append(cur+str(n))\n    return ''.join(out)\n```",
    "parse_log": "```python\ndef parse_log(line):\n    parts=line.split(' ',3)\n    return {'date':parts[0],'time':parts[1],'level':parts[2],'message':parts[3]}\n```",
    "lis_length": "```python\ndef lis_length(nums):\n    import bisect\n    tails=[]\n    for x in nums:\n        i=bisect.bisect_left(tails,x)\n        if i==len(tails): tails.append(x)\n        else: tails[i]=x\n    return len(tails)\n```",
}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        msgs = body.get("messages", [])
        user = next((m["content"] for m in msgs if m["role"] == "user"), "")
        has_tool_result = any(m["role"] == "tool" for m in msgs)
        tools = body.get("tools", [])
        msg = {"role": "assistant", "content": "", "tool_calls": None}

        if has_tool_result:
            tr = json.loads([m for m in msgs if m["role"] == "tool"][-1]["content"])
            if "error" in tr:
                msg["content"] = "Sorry, that ticket was not found in the system."
            else:
                f = tr.get("result", {}).get("ticket", {}).get("fields", {})
                msg["content"] = f"Assigned to {f.get('assignee',{}).get('name')}, priority {f.get('priority')}."
        elif tools and "RAID" not in user:
            # naive: always call the seemingly relevant tool
            name = tools[0]["function"]["name"]
            args = {}
            if "Boston" in user: name, args = "get_weather", {"location": "Boston, MA"}
            elif "TiB" in user: name, args = "convert_storage", {"value": 3.5, "from_unit": "TiB", "to_unit": "GB"}
            elif "nginx" in user:
                name = "restart_service"; args = {"service_name": "nginx", "host": "web01"}
                if not any(t["function"]["name"] == name for t in tools): name = tools[0]["function"]["name"]
            elif "INC-" in user:
                name = "lookup_ticket"; args = {"ticket_id": re.search(r"INC-\d+", user).group(0)}
            msg["tool_calls"] = [{"id": "call_1", "type": "function",
                                  "function": {"name": name, "arguments": json.dumps(args)}}]
        elif "RAID" in user:
            msg["content"] = "RAID 5 stripes data across disks with distributed parity."
        elif "ANSWER: <integer>" in user:
            # math category — mock some right, some wrong so we can verify scorer
            # extracts the LAST ANSWER line and grades correctly
            answers = {
                "10 identical balls": "44",
                "trailing zeros does 100!": "48",
                "shortest lattice paths": "126",
                "5-person committees": "666",
                "F(100)": "75",  # correct
                "F(60)": "961",   # off-by-one; correct is 920
                "sum of the first 50 prime numbers": "5117",
                "sum of the decimal digits of 20!": "54",
                "Start with the number 27": "111",
            }
            hit = next((v for k, v in answers.items() if k in user), "42")
            msg["content"] = f"Let me work through it step by step... [reasoning omitted]\n\nANSWER: {hit}"
        elif "code block" in user:
            match = re.search(r"`(\w+)`", user)
            fn = match.group(1) if match else ""
            msg["content"] = GOOD_CODE.get(fn, "I would write a function but I forgot how.")
        elif "vault access code" in user:
            m = re.search(r"Project Aurora is (\d+)", user)
            msg["content"] = m.group(1) if m else "unknown"
        elif "JSON object" in user:
            msg["content"] = '{"status": "ok", "count": 17}'
        elif "three words" in user:
            msg["content"] = "It is blue"
        elif "ready" in user:
            msg["content"] = "ready"
        else:
            nums = {"drives": "46", "notebooks": "4.00", "tank": "12", "workers": "the answer is 16 days"}
            msg["content"] = next((v for k, v in nums.items() if k in user), "42")

        resp = {"choices": [{"message": msg}],
                "usage": {"prompt_tokens": max(1, len(user)//4), "completion_tokens": 30},
                "timings": {"prompt_per_second": 512.4, "predicted_per_second": 9.7}}
        out = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

HTTPServer(("localhost", 8099), H).serve_forever()
