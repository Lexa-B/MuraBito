#include "GameRules.h"

#include "MurabitoLog.h"

void AGameRules::BeginPlay()
{
	Super::BeginPlay();
	UE_LOG(LogMurabito, Log, TEXT("GameRules: started"));
}
