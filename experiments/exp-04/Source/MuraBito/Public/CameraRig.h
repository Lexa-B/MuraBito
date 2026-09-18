#pragma once

#include "CoreMinimal.h"
#include "CameraMath.h"
#include "GameFramework/Pawn.h"
#include "CameraRig.generated.h"

class UCameraComponent;
class USpringArmComponent;

/**
 * Overhead camera: pans over the map's XY bounds and zooms along a spring arm.
 * Tilt follows zoom, steep when far and oblique when close. No yaw rotation.
 * (Subclasses APawn only because the engine possesses pawns.)
 */
UCLASS()
class MURABITO_API ACameraRig : public APawn
{
	GENERATED_BODY()

public:
	ACameraRig();

	virtual void Tick(float DeltaSeconds) override;

	/** Pan limits (XY) and the fixed height of the pivot. */
	void Configure(const FBox2D& InBounds, float InBaseZ);

	/** Screen-relative pan direction for this frame: X right, Y up-screen, each in [-1, 1]. */
	void AddPan(const FVector2D& ScreenDir);

	/** Direct world XY offset for this frame (mouse drag). */
	void AddPanWorld(const FVector2D& WorldDelta);

	/** Wheel steps: positive zooms out. */
	void AddZoom(float Steps);

	float GetArmLength() const;

	UPROPERTY(EditAnywhere, Category = "Camera") float NearArm = 1500.f;
	UPROPERTY(EditAnywhere, Category = "Camera") float FarArm = 12000.f;
	UPROPERTY(EditAnywhere, Category = "Camera") float NearPitch = -45.f;
	UPROPERTY(EditAnywhere, Category = "Camera") float FarPitch = -75.f;
	/** cm/s at the near limit; scales with arm length. */
	UPROPERTY(EditAnywhere, Category = "Camera") float PanSpeed = 1500.f;
	/** Fraction of the zoom range per wheel step. */
	UPROPERTY(EditAnywhere, Category = "Camera") float ZoomStep = 0.08f;
	UPROPERTY(EditAnywhere, Category = "Camera") float ZoomSmoothing = 10.f;

	UPROPERTY(VisibleAnywhere, Category = "Camera") TObjectPtr<USceneComponent> Pivot;
	UPROPERTY(VisibleAnywhere, Category = "Camera") TObjectPtr<USpringArmComponent> Arm;
	UPROPERTY(VisibleAnywhere, Category = "Camera") TObjectPtr<UCameraComponent> Camera;

private:
	FZoomRange ZoomRange() const;
	void ApplyZoom();

	FBox2D Bounds = FBox2D(FVector2D(-1.0e6), FVector2D(1.0e6));
	float BaseZ = 0.f;
	float Zoom01 = 0.6f;
	float TargetZoom01 = 0.6f;
	FVector2D PendingScreenPan = FVector2D::ZeroVector;
	FVector2D PendingWorldPan = FVector2D::ZeroVector;
};
