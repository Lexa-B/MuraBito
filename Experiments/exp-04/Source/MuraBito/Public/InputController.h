#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "InputController.generated.h"

class AHexOverlay;
class ATerrain;
class ACameraRig;
class UInputAction;
class UInputMappingContext;
struct FInputActionValue;

/**
 * Keyboard/mouse input for the camera rig, plus picking the hex under the cursor.
 * Input actions and the mapping context are created in code, not as assets.
 */
UCLASS()
class MURABITO_API AInputController : public APlayerController
{
	GENERATED_BODY()

public:
	AInputController();

	void SetWorldRefs(ATerrain* InTerrain, AHexOverlay* InOverlay);

	/** Pixels from the viewport edge that start edge scrolling. */
	UPROPERTY(EditAnywhere, Category = "Input") float EdgeScrollMargin = 8.f;
	/** Drag pan: world cm per pixel, per cm of arm length. */
	UPROPERTY(EditAnywhere, Category = "Input") float DragCmPerPixelPerArm = 0.0012f;

protected:
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;
	virtual void PlayerTick(float DeltaTime) override;

private:
	void CreateInputObjects();
	void OnMove(const FInputActionValue& Value);
	void OnZoom(const FInputActionValue& Value);
	void UpdateEdgeScroll();
	void UpdateDrag();
	void UpdateHover();
	ACameraRig* Rig() const;

	UPROPERTY() TObjectPtr<UInputMappingContext> Context;
	UPROPERTY() TObjectPtr<UInputAction> MoveAction;
	UPROPERTY() TObjectPtr<UInputAction> ZoomAction;

	TWeakObjectPtr<ATerrain> Terrain;
	TWeakObjectPtr<AHexOverlay> Overlay;

	bool bDragging = false;
	FVector2D LastMouse = FVector2D::ZeroVector;
};
