import json
import boto3
import time
import botocore
import csv
import io

def lambda_handler(event, context):
    
    ec2_client = boto3.client('ec2')
    ssm_client = boto3.client('ssm')
    s3_client = boto3.client('s3')
    
    csvio = io.StringIO()
    writer = csv.writer(csvio)
    writer.writerow(['Name', 'Image ID', 'Instance ID', 'Instance Type', 'IamInstanceProfile', 'Vpc Id', 'Platform', 'SSM Agent', 'Inspector Agent', 'Key Name', 'Private Ip', 'Public Ip', 'Instance State'])
    
    describeInstances = ec2_client.describe_instances()
    
    IgnoreAMIList = []      # Place all AMI Ids which do not have to be scanned
    InstancesReport = []
    
    for i in describeInstances['Reservations']:
        for instance in i['Instances']:
            
            if instance['ImageId'] not in IgnoreAMIList:
                instanceInfo = {}
                instanceInfo['Name'] = instance['Tags'][0]['Value']
                instanceInfo['ImageId'] = instance['ImageId']
                instanceInfo['InstanceId'] = instance['InstanceId']
                instanceInfo['InstanceType'] = instance['InstanceType']
                try:
                    instanceInfo['IamInstanceProfile'] = instance['IamInstanceProfile']['Arn']
                except KeyError as e:
                    instanceInfo['IamInstanceProfile'] = ''
            
                try:
                    instanceInfo['SubnetId'] = instance['SubnetId']
                except KeyError as e:
                    instanceInfo['SubnetId'] = ''
            
                try:
                    instanceInfo['VpcId'] = ''
                except KeyError as e:
                    instanceInfo['VpcId'] = instance['VpcId']
            
                instanceInfo['KeyName'] = instance['KeyName']
            
                try:
                    instanceInfo['PrivateIpAddress'] = instance['PrivateIpAddress']
                except KeyError as e:
                    instanceInfo['PrivateIpAddress'] = ''
            
            
                try:
                    if(instance['Platform'] == 'windows'):
                    
                        instanceInfo['Platform'] = 'windows'
                    
                        if instance['State']['Name'] == 'running':
                            instanceInfo['InstanceState'] = 'running'
                            instanceInfo['PublicIpAddress'] = instance['PublicIpAddress']
                        
                    
                        
                            response = ssm_client.send_command(
                                InstanceIds = [instance['InstanceId']],
                                DocumentName = 'AWS-RunPowerShellScript',
                                Parameters = {"commands": ["Get-Service AmazonSSMAgent"]}
                            )
                    
                            command_id = response['Command']['CommandId']
                        
        
                            time.sleep(5)
        
                            output = ssm_client.get_command_invocation(
                                CommandId = command_id,
                                InstanceId = instance['InstanceId']
                            )
                        
                
                            if('AmazonSSMAgent' in str(output['StandardOutputContent']) and 'Running' in str(output['StandardOutputContent'])):
                                instanceInfo['SSM_Agent'] = 'Installed'
                            else:
                                instanceInfo['SSM_Agent'] = ''
                    
                            response2 = ssm_client.send_command(
                                InstanceIds = [instance['InstanceId']],
                                DocumentName = 'AWS-RunPowerShellScript',
                                Parameters = {"commands": ["Get-Service AWSAgent"]}
                            )
                        
                            command_id2 = response2['Command']['CommandId']
        
                            time.sleep(5)
        
                            output2 = ssm_client.get_command_invocation(
                                CommandId = command_id2,
                                InstanceId = instance['InstanceId']
                            )
                        
                            if('AWSAgent' in str(output2['StandardOutputContent']) and 'Running' in str(output2['StandardOutputContent'])):
                                instanceInfo['Inspector'] = 'Installed'
                            else:
                                instanceInfo['Inspector'] = ''
                        
                        else:
                            instanceInfo['SSM_Agent'] = ''
                            instanceInfo['Inspector'] = ''
                            instanceInfo['InstanceState'] = 'Stopped'
                            instanceInfo['PublicIpAddress'] = ''
                    
                    
                except KeyError as e:
                
                    instanceInfo['Platform'] = 'Linux/UNIX'
                    if instance['State']['Name'] == 'running':
                        instanceInfo['InstanceState'] = 'running'
                        instanceInfo['PublicIpAddress'] = instance['PublicIpAddress']
                    
                        try:
                            response = ssm_client.send_command(
                                InstanceIds = [instance['InstanceId']],
                                DocumentName = 'AWS-RunShellScript',
                                Parameters = {"commands": ["sudo /opt/aws/awsagent/bin/awsagent status"]}
                            )
                        
                            command_id = response['Command']['CommandId']
        
                            time.sleep(5)
        
                            output = ssm_client.get_command_invocation(
                                CommandId = command_id,
                                InstanceId = instance['InstanceId']
                            )
                    
                    
                            if('IpAddress' in str(output['StandardOutputContent'])):
                                instanceInfo['Inspector'] = 'installed'
                            else:
                                instanceInfo['Inspector'] = ''
                        except botocore.exceptions.ClientError as e:
                            instanceInfo['Inspector'] = ''
                    
                    
                        try:
                            response2 = ssm_client.send_command(
                                InstanceIds = [instance['InstanceId']],
                                DocumentName = 'AWS-RunShellScript',
                                Parameters = {"commands": ["yum info amazon-ssm-agent"]}
                            )
                    
                            command_id2 = response2['Command']['CommandId']
        
                            time.sleep(5)
        
                            output2 = ssm_client.get_command_invocation(
                                CommandId = command_id2,
                                InstanceId = instance['InstanceId']
                            )
                    
                    
                            if('Version' in str(output2['StandardOutputContent'])):
                                instanceInfo['SSM_Agent'] = 'installed'
                            else:
                                instanceInfo['SSM_Agent'] = ''
                        except botocore.exceptions.ClientError as e:
                            instanceInfo['SSM_Agent'] = ''
                    
                    
                    else:
                        instanceInfo['SSM_Agent'] = ''
                        instanceInfo['Inspector'] = ''
                        instanceInfo['InstanceState'] = 'Stopped'
                        instanceInfo['PublicIpAddress'] = ''
                   
                InstancesReport.append(instanceInfo)
                writer.writerow([instanceInfo['Name'], instanceInfo['ImageId'], instanceInfo['InstanceId'], instanceInfo['InstanceType'], instanceInfo['IamInstanceProfile'], instanceInfo['VpcId'], instanceInfo['Platform'], instanceInfo['SSM_Agent'], instanceInfo['Inspector'], instanceInfo['KeyName'], instanceInfo['PrivateIpAddress'], instanceInfo['PublicIpAddress'], instanceInfo['InstanceState']])
                
            
            
    
    #print(InstancesReport)
    print(csvio.getvalue())
    s3_client.put_object(Body=csvio.getvalue(), ContentType='text/csv', Bucket='test-bucket-2456', Key='EC2.csv') 