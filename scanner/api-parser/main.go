package main

func main() {
	InitLogger()
	InitConfig()
	InitRedis()
	defer RDB.Close()

	groupList := fetchGroups()

	if len(groupList) == 0 {
		Notify("WARN", "Список групп пустой", "Возможны изменения в API вуза")
	}
}
