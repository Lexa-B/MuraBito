#include "WorldBuilder.h"

#include "CameraRig.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/SkyLight.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HexOverlay.h"
#include "InputController.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "MuraBitoLog.h"
#include "Terrain.h"

AWorldBuilder::AWorldBuilder()
{
	DefaultPawnClass = ACameraRig::StaticClass();
	PlayerControllerClass = AInputController::StaticClass();
}

int32 AWorldBuilder::ReadSeed()
{
	FString Value;
	if (!FParse::Value(FCommandLine::Get(), TEXT("Seed="), Value))
	{
		UE_LOG(LogMuraBito, Log, TEXT("WorldBuilder: no -Seed given, using 0"));
		return 0;
	}
	if (!Value.IsNumeric())
	{
		UE_LOG(LogMuraBito, Warning, TEXT("WorldBuilder: -Seed=%s is not a number, using 0"), *Value);
		return 0;
	}
	return FCString::Atoi(*Value);
}

void AWorldBuilder::BeginPlay()
{
	Super::BeginPlay();

	const int32 Seed = ReadSeed();
	Grid = FHexGrid(TileSize, MapRadius);
	Height = FTerrainHeight(Seed);

	const FBox2D MapBounds = Grid.Bounds();
	const FBox2D TerrainArea = MapBounds.ExpandBy(2.0 * TileSize);

	Terrain = GetWorld()->SpawnActor<ATerrain>();
	Terrain->Build(Height, TerrainArea, TerrainSpacing);

	Overlay = GetWorld()->SpawnActor<AHexOverlay>();
	Overlay->Build(Grid, Height);

	SpawnLighting();
	bBuilt = true;

	UE_LOG(LogMuraBito, Log, TEXT("WorldBuilder: seed %d, %d tiles, tile size %.0f cm"), Seed, Grid.NumTiles(), TileSize);

	for (FConstPlayerControllerIterator It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
	{
		SetUpPlayer(It->Get());
	}
}

void AWorldBuilder::RestartPlayer(AController* NewPlayer)
{
	if (APlayerController* Player = Cast<APlayerController>(NewPlayer))
	{
		SetUpPlayer(Player);
	}
}

void AWorldBuilder::SetUpPlayer(APlayerController* Player)
{
	if (!Player)
	{
		return;
	}
	ACameraRig* Rig = Cast<ACameraRig>(Player->GetPawn());
	if (!Rig)
	{
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		Rig = GetWorld()->SpawnActor<ACameraRig>(FVector::ZeroVector, FRotator::ZeroRotator, Params);
		Player->Possess(Rig);
	}
	if (bBuilt)
	{
		Rig->Configure(Grid.Bounds(), AverageTileHeight());
		if (AInputController* Input = Cast<AInputController>(Player))
		{
			Input->SetWorldRefs(Terrain, Overlay);
		}
	}
}

float AWorldBuilder::AverageTileHeight() const
{
	double Sum = 0.0;
	const TArray<FHex> Tiles = Grid.Tiles();
	for (const FHex& Hex : Tiles)
	{
		const FVector2D P = Grid.HexToXY(Hex);
		Sum += Height.Height(P.X, P.Y);
	}
	return Tiles.Num() > 0 ? static_cast<float>(Sum / Tiles.Num()) : 0.f;
}

void AWorldBuilder::SpawnLighting()
{
	UWorld* World = GetWorld();

	ADirectionalLight* Sun = World->SpawnActor<ADirectionalLight>(FVector(0, 0, 2000), FRotator(-40.f, 35.f, 0.f));
	if (UDirectionalLightComponent* SunLight = Cast<UDirectionalLightComponent>(Sun->GetLightComponent()))
	{
		SunLight->SetMobility(EComponentMobility::Movable);
		SunLight->SetAtmosphereSunLight(true);
	}

	World->SpawnActor<ASkyAtmosphere>();

	ASkyLight* Sky = World->SpawnActor<ASkyLight>();
	if (USkyLightComponent* SkyLight = Sky->GetLightComponent())
	{
		SkyLight->SetMobility(EComponentMobility::Movable);
		SkyLight->SetRealTimeCapture(true);
		SkyLight->RecaptureSky();
	}

	World->SpawnActor<AExponentialHeightFog>();
}
