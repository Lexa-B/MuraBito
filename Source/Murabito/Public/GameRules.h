#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameRules.generated.h"

/**
 * The project's game mode. Empty for now: it keeps the engine's defaults, so Play gives
 * the engine's flying camera (ADefaultPawn) for looking around a map.
 */
UCLASS()
class MURABITO_API AGameRules : public AGameModeBase
{
	GENERATED_BODY()

protected:
	virtual void BeginPlay() override;
};
