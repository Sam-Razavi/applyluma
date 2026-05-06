{% macro extract_skills(column_name) %}
{#-
  Returns a PostgreSQL text[] of detected tech skills found in column_name.
  Uses word-boundary regex so "xml" does not match "ml", etc.
  Call once in a CTE, then reference the alias downstream.
-#}
array_remove(ARRAY[
    case when lower({{ column_name }}) ~ '\bpython\b'                       then 'python'           end,
    case when lower({{ column_name }}) ~ '\bjavascript\b'                   then 'javascript'       end,
    case when lower({{ column_name }}) ~ '\btypescript\b'                   then 'typescript'       end,
    case when lower({{ column_name }}) ~ '\bjava\b'                         then 'java'             end,
    case when lower({{ column_name }}) ~ '\bgolang\b|\bgo lang\b'           then 'golang'           end,
    case when lower({{ column_name }}) ~ '\brust\b'                         then 'rust'             end,
    case when lower({{ column_name }}) ~ '\bfastapi\b'                      then 'fastapi'          end,
    case when lower({{ column_name }}) ~ '\breact\.?js\b|\breact\b'         then 'react'            end,
    case when lower({{ column_name }}) ~ '\bvue\.?js\b|\bvue\b'             then 'vue'              end,
    case when lower({{ column_name }}) ~ '\bangular\b'                      then 'angular'          end,
    case when lower({{ column_name }}) ~ '\bdjango\b'                       then 'django'           end,
    case when lower({{ column_name }}) ~ '\bflask\b'                        then 'flask'            end,
    case when lower({{ column_name }}) ~ '\bnode\.?js\b'                    then 'node.js'          end,
    case when lower({{ column_name }}) ~ '\bpostgresql\b|\bpostgres\b'      then 'postgresql'       end,
    case when lower({{ column_name }}) ~ '\bmongodb\b|\bmongo\b'            then 'mongodb'          end,
    case when lower({{ column_name }}) ~ '\bmysql\b'                        then 'mysql'            end,
    case when lower({{ column_name }}) ~ '\bredis\b'                        then 'redis'            end,
    case when lower({{ column_name }}) ~ '\belasticsearch\b'                then 'elasticsearch'    end,
    case when lower({{ column_name }}) ~ '\baws\b|\bamazon web services\b'  then 'aws'              end,
    case when lower({{ column_name }}) ~ '\bgcp\b|\bgoogle cloud\b'         then 'gcp'              end,
    case when lower({{ column_name }}) ~ '\bazure\b|\bmicrosoft azure\b'    then 'azure'            end,
    case when lower({{ column_name }}) ~ '\bdocker\b'                       then 'docker'           end,
    case when lower({{ column_name }}) ~ '\bkubernetes\b|\bk8s\b'           then 'kubernetes'       end,
    case when lower({{ column_name }}) ~ '\bgraphql\b'                      then 'graphql'          end,
    case when lower({{ column_name }}) ~ '\bterraform\b'                    then 'terraform'        end,
    case when lower({{ column_name }}) ~ '\bgit\b'                          then 'git'              end,
    case when lower({{ column_name }}) ~ '\bci/?cd\b'                       then 'ci/cd'            end,
    case when lower({{ column_name }}) ~ '\bairflow\b'                      then 'airflow'          end,
    case when lower({{ column_name }}) ~ '\bdbt\b'                          then 'dbt'              end,
    case when lower({{ column_name }}) ~ '\bkafka\b'                        then 'kafka'            end,
    case when lower({{ column_name }}) ~ '\brabbitmq\b'                     then 'rabbitmq'         end,
    case when lower({{ column_name }}) ~ '\bcelery\b'                       then 'celery'           end,
    case when lower({{ column_name }}) ~ '\bmachine learning\b|\bml\b'      then 'machine-learning' end,
    case when lower({{ column_name }}) ~ '\bllm\b|\blarge language model\b' then 'llm'              end,
    case when lower({{ column_name }}) ~ '\bopenai\b'                       then 'openai'           end,
    case when lower({{ column_name }}) ~ '\blangchain\b'                    then 'langchain'        end
], null)
{% endmacro %}
