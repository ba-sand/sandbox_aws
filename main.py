import subprocess
import os
import glob
import yaml

def run_bash(command:str):
   process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
   output, error = process.communicate()
   return output.decode("utf-8")

if __name__ == "__main__":
   path = 'lambda_routes/'
   lambdas_to_deploy = []

   # read in lambdas and determine which should be deployed
   for filename in glob.glob(os.path.join(path, '*.yaml')):
      with open(os.path.join(os.getcwd(), filename), 'r') as f: # open in readonly mode
         output = yaml.safe_load(f)
         if output['deploy'] is True:
            lambdas_to_deploy.append(output)

   # deploy the lambdas that are indicated as such
   for cur_lambda in lambdas_to_deploy:
      # extract data from yamls
      api_name = cur_lambda['name']
      api_desc = cur_lambda['description']
      lambda_url = cur_lambda['url']
      function_aws = cur_lambda['function_aws']

      # get list of existing APIs
      cmd_1 = 'aws apigateway get-rest-apis'
      out_1 = yaml.safe_load(run_bash(cmd_1))
      existing_apis = []
      for i in range(0, len(out_1['items'])):
         existing_apis.append(out_1['items'][i]['name'])

      # if API for lambda has not been created before run through workflow
      if api_name not in existing_apis:
         # create api and save its id
         cmd_2 = f'aws apigateway create-rest-api --name {api_name} --description "{api_desc}"'
         out_2 = run_bash(cmd_2)
         api_id = yaml.safe_load(out_2)['id']
         print('my api_id is: ' + api_id)

         # run get resources to get resource_id
         cmd_3 = f'aws apigateway get-resources --rest-api-id "{api_id}"'
         out_3 = run_bash(cmd_3)
         parent_id = yaml.safe_load(out_3)['items'][0]['id']
         print('my_api_parent_id is: ' + parent_id)

         # create resource
         cmd_4 = f'aws apigateway create-resource --rest-api-id {api_id} --parent-id {parent_id} --path-part {{proxy+}}'
         out_4 = run_bash(cmd_4)
         resource_id = yaml.safe_load(out_4)['id']
         print(out_4)

         # apply put-method to api
         cmd_5 = f'aws apigateway put-method --rest-api-id {api_id} --resource-id {resource_id} --http-method "ANY" --authorization-type "NONE"'
         out_5 = run_bash(cmd_5)
         print(out_5)
         
         # apply put-integration to api, note: look into differences between AWS and AWS_PROXY. response body seems to change slightly.
         cmd_6 = f'aws apigateway put-integration --rest-api-id {api_id} --resource-id {resource_id} --http-method ANY --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{lambda_url}/invocations"'
         out_6 = run_bash(cmd_6)
         print(out_6)

         # give lambda permissions to be run by your api.
         cmd_7 = f'aws lambda add-permission --function-name {function_aws} --statement-id "{api_id}" --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:us-east-1:482102633168:{api_id}/*"'
         out_7 = run_bash(cmd_7)
         print(out_7)
         
         # deploy api to connect lambda with api gateway
         cmd_8 = f'aws apigateway create-deployment --rest-api-id {api_id} --stage-name "dev"'
         out_8 = run_bash(cmd_8)
         print(out_8)
         

# TO DO
# 1. figure out how to modify the payload being submitted via api gateway (for parametrized lambdas). I believe the payload has to be very explicitly defined; COMPLETE
# 2. modify the lambda_routes yamls as needed to accept some common format that defines the payload; COMPLETE, via aws_proxy
# 3. dynamically modify each statement here to deploy lambdas as needed with their respective payload ; COMPLETE, cia aws_proxy
# 4. figure out how to block all api-gateway APIs from the public internet TO DO
# 5. move to vontive infra TO DO
# 6. only allow access via VPC peering TO DO


# next steps to test 4-6:
# sample: curl https://4npjdwmgh7.execute-api.us-east-1.amazonaws.com/dev/placeholder\?name_2\=bryan
# make an ec2 instance in us-west-1. from here, run the curl command to test.
# IF everything is successfuly, then curl from EC2 works, but curl from your local laptop does NOT work.
# vpc peering may be the answer here, not sure.
# also clean up existing AWS infra
