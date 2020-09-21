1. install environment:
	pip install rasa==1.10.4
	pip install mysql-connector-python
	pip install rasa[spacy]
	pip install PyMySQL
	pip install pyvi

* Create Database in mysql
	Create database có tên là example (cái này sau có thể sửa nhưng tạm thời để thế có gì sau đặt tên khác)
	- câu lệnh tạo bảng informuser trên phpmyadmin
		CREATE TABLE informuser(
			id INT(11) UNSIGNED AUTO_INCREMENT PRIMARY KEY,
		    id_conversation Text COLLATE utf8_vietnamese_ci
		)

* Kiểm tra file config/config.json phần "database": chỉnh "port", "username", "password" theo đúng mysql cài đặt

-----------------------------------------------------------------------------------------------
-----------------------------------------------------------------------------------------------
2. Các bước để thêm mới intent và mới action (câu hỏi và câu trả lời)
	1. Vào resources/graph.graph.md
		> START > {intent_name} > {action_name}
	    -> sau khi thêm xong chay câu lệnh: python build_graph.py resources/graphs/graph.md
	2. vào domain.yml
		- thêm {intent_name} vào chô intent:
		- thêm {action_name} vào chô action:
	3. vào action.py: thêm các action mới vào
		class {action_name}(Action):
		    def name(self) -> Text:
		        return "{action_name}"

		    def run(self, dispatcher, tracker, domain):
		        response = execute_normal_action(tracker, self.name())
		        dispatcher.utter_message(text=response)
		        return [Restarted()]
    4. Viết text trả về cho request đến trong file config/config_template_action.json
    	"{action_name}": [
		    {
		      "status": "END", ## trạng thái để nguyên là END
		      "text": "", ## text phản hồi sau của action đó cho phần hiển thị text
		      "text_tts": "" ## text phản hồi sau của action đó cho phần nói
		    }
		  ]
	5. Vào file config/config.json: thêm {action_name} trong biến "name_action_finsh" : [..., {action_name}]
	6. tạo file {intent_name}.md trong data/nlu/{intent_name}.md. Thêm dữ liệu vào intent

3. huấn luyện mô hình: rasa train --debug

4. Chạy để chạy rasa: 
	chạy 2 câu lệnh thường hôm trước:
		để run server ta chạy câu lệnh: rasa run -m models --enable-api --cors "*" -p 8989 --debug
		để run action ta chạy câu lệnh: rasa run actions --debug
5.  Tắt rasa
	- Nếu chạy bằng câu lệnh thường thì ctrl + C để thoát

* Note:
	- Nhìn cái intent_hellow và action_hellow như thế nào làm y như vậy

Example:
	http://localhost:5055/webhooks/rest/webhook
	input request:
		{
		    "sender": "2", 
		    "message": "tạm biệt"
		}
	Response:
		{
	        "recipient_id": "2",
	        "text":"{\"status\": \"END\", \"text\": \"t\ạm bi\ệt anh\", \"text_tts\": \"t\ạm bi\ệt anh\", \"action\": \"action_bye\", \"intent\": \"intent_bye\"}"
	    }
	    Decode json lấy tứ text ra có tham số sau:
	    	- status: là trạng thái kết thúc hay chưa kết thúc (cái này không cần để ý)
	    	- text: là text để hiển thị
	    	- text_tts: là text để đưa vào để chuyển thành lời nói
