import json
import os
from dotenv import load_dotenv
from agent_orchestrator import run_agent_review

# Load environment variables
load_dotenv()

def lambda_handler(event, context):
    """
    AWS Lambda handler for the AI Review Agent
    
    Expected event format:
    {
        "body": "{\"problem\": \"your technical problem here\"}"
    }
    """
    try:
        # Parse the incoming request
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})
        
        problem = body.get("problem", "")
        
        if not problem:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No problem statement provided"})
            }
        
        # Run the agent review
        result = run_agent_review(problem)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "problem": result["problem"],
                "architecture_review": result["architecture_review"],
                "cost_review": result["cost_review"],
                "security_review": result["security_review"],
                "final_report": result["final_report"]
            }, indent=2)
        }
    
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
