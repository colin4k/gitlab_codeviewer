# coding=utf-8

from fastapi import APIRouter, Request,BackgroundTasks
import openai
import os
import requests

openai.api_key = os.environ.get("OPENAI_API_KEY")
openai.api_base = os.environ.get("OPENAI_API_BASE")
gitlab_token = os.environ.get("GITLAB_TOKEN")
gitlab_url = os.environ.get("GITLAB_URL")+'/api/v4'

hook = APIRouter()  
@hook.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    print(request.headers.get("X-Gitlab-Token"))
    print(os.environ.get("EXPECTED_GITLAB_TOKEN"))
    if request.headers.get("X-Gitlab-Token") != os.environ.get("EXPECTED_GITLAB_TOKEN"):
        print('校验失败')
        return "Unauthorized", 403
    #payload = request.json
    payload = await request.json()
    print(payload.get("object_kind"))
    if payload.get("object_kind") == "merge_request":
        if payload["object_attributes"]["action"] != "open":
            return "Not a  PR open", 200
        project_id = payload["project"]["id"]
        mr_id = payload["object_attributes"]["iid"]
        changes_url = f"{gitlab_url}/projects/{project_id}/merge_requests/{mr_id}/changes"

        headers = {"Private-Token": gitlab_token}
        response = requests.get(changes_url, headers=headers)
        mr_changes = response.json()

        diffs = [change["diff"] for change in mr_changes["changes"]]

        pre_prompt = "请以资深开发人员的视角尽你所能审查代码变更并回答代码审查相关的问题。代码变更将以git diff 字符串的形式提供："
        questions = "\n\n问题:\n1. 你能简明扼要地总结以下更改内容吗？\n2. 在差异中，添加或更改的代码是否以清晰易懂的方式编写？\n3. 代码是否使用了注释或描述性的函数和变量名称来解释其含义？\n4. 根据更改的代码复杂性，是否可以简化代码而不影响其功能？如果可以，请给出示例片段。\n5. 是否能找到任何错误？如果是，请解释并提供行号参考。\n6. 你是否看到任何可能引发安全问题的代码？\n"

        messages = [
            {"role": "system", "content": "你是是一位资深编程专家，负责代码变更的审查工作。需要给出审查建议。在建议的开始需明确对此代码变更给出「拒绝」或「接受」的决定，并且以格式「变更评分：实际的分数」给变更打分，分数区间为0~100分。然后，以精炼的语言、严厉的语气指出存在的问题。如果你觉得必要的情况下，可直接给出修改后的内容。建议中的语句可以使用emoji结尾。你的反馈内容必须使用严谨的markdown格式。"},
            {"role": "user", "content": f"{pre_prompt}\n\n{''.join(diffs)}{questions}"},
            {"role": "assistant", "content": "当回答问题时，请使用漂亮且有组织的 Markdown 格式，以便在 GitLab 中正确显示（如果需要，请使用代码块）。请只发送回答，不要包含对请求的评论。在回答中包含问题的简短版本，以便我们知道问题是什么。"},
        ]
        try:
            completions = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                temperature=0.7,
                stream=False,
                messages=messages
            )
            answer = completions.choices[0].message["content"].strip()
            answer += "\n\n作为引用，我将提供以下问题: \n"
            for question in questions.split("\n"):
                answer += f"\n{question}"
            answer += "\n\n此评论由AI生成."
        except Exception as e:
            print(e)
            answer = "很抱歉，我现在有故障无法处理请求。"
            answer += "\n\n此评论由AI生成."
            answer += "\n\n错误: " + str(e)

        print(answer)
        comment_url = f"{gitlab_url}/projects/{project_id}/merge_requests/{mr_id}/notes"
        comment_payload = {"body": answer}
        comment_response = requests.post(comment_url, headers=headers, json=comment_payload)
    elif payload.get("object_kind") == "push":
        print(payload)
        project_id = payload["project_id"]
        commit_id = payload["after"]
        commit_url = f"{gitlab_url}/projects/{project_id}/repository/commits/{commit_id}/diff"
        print(commit_url)

        headers = {"Private-Token": gitlab_token}
        response = requests.get(commit_url, headers=headers)
        changes = response.json()

        changes_string = ''.join([str(change) for change in changes])

        pre_prompt = "请以资深开发人员的视角尽你所能审查代码变更并回答代码审查相关的问题。代码变更将以git diff 字符串的形式提供："
        questions = "\n\n问题:\n1. 你能简明扼要地总结以下更改内容吗？\n2. 在差异中，添加或更改的代码是否以清晰易懂的方式编写？\n3. 代码是否使用了注释或描述性的函数和变量名称来解释其含义？\n4. 根据更改的代码复杂性，是否可以简化代码而不影响其功能？如果可以，请给出示例片段。\n5. 是否能找到任何错误？如果是，请解释并提供行号参考。\n6. 你是否看到任何可能引发安全问题的代码？\n"

        messages = [
            {"role": "system", "content": "你是是一位资深编程专家，负责代码变更的审查工作。需要给出审查建议。在建议的开始需明确对此代码变更给出「拒绝」或「接受」的决定，并且以格式「变更评分：实际的分数」给变更打分，分数区间为0~100分。然后，以精炼的语言、严厉的语气指出存在的问题。如果你觉得必要的情况下，可直接给出修改后的内容。建议中的语句可以使用emoji结尾。你的反馈内容必须使用严谨的markdown格式。"},
            {"role": "user", "content": f"{pre_prompt}\n\n{changes_string}{questions}"},
            {"role": "assistant", "content": "当回答问题时，请使用漂亮且有组织的 Markdown 格式，以便在 GitLab 中正确显示（如果需要，请使用代码块）。请只发送回答，不要包含对请求的评论。在回答中包含问题的简短版本，以便我们知道问题是什么。"},
        ]
        print(messages)
        try:
            completions = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                temperature=0.7,
                stream=False,
                messages=messages
            )
            answer = completions.choices[0].message["content"].strip()
            answer += "\n\n作为引用，我将提供以下问题: \n"
            for question in questions.split("\n"):
                answer += f"\n{question}"
            answer += "\n\n此评论由AI生成."
        except Exception as e:
            print(e)
            answer = "很抱歉，我现在有故障无法处理请求。"
            answer += "\n\n此评论由AI生成."
            answer += "\n\n错误: " + str(e)

        print(answer)
        comment_url = f"{gitlab_url}/projects/{project_id}/repository/commits/{commit_id}/comments"
        comment_payload = {"note": answer}
        comment_response = requests.post(comment_url, headers=headers, json=comment_payload)

    return "OK", 200
