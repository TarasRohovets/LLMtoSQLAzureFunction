class RespondeDto:
  def __init__(self, chat_answer, sql_query_result=None, sqlQuery=None, idsList = None):
        self.chatAnswer = chat_answer
        self.sqlQueryResult = sql_query_result
        self.sqlQuery = sqlQuery
        self.idsList = idsList