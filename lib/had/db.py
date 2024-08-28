import boto3

class DynamoFactory:
  def __init__(self, table_name):
    from project import settings
    self.table_name = table_name
    self.client = boto3.client("dynamodb", region_name=settings.AWS["region"])
  def insert(self, item):
    try:
      self.client.put_item(
        TableName=table_name,
        Item=item,
        ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)"
      )
      return True
    except ClientError as e:
      if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
        return False
      else:
        raise e

