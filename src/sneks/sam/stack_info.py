import boto3
import os

STACK_NAME = os.environ["STACK_NAME"]

STACK = boto3.client("cloudformation").describe_stacks(StackName=STACK_NAME)["Stacks"][0]
STACK_OUTPUTS = {o["OutputKey"]:o["OutputValue"] for o in STACK.get("Outputs",[])}
